"""
Simulated negotiation runner.

Produces an async generator of events (turn-by-turn messages, holds, deal reached, etc.)
that the WebSocket layer streams to the browser.

Works in two modes:
  - LLM mode: uses OpenAI/Gemini to drive both Arbiter and Rep agents
  - Fallback mode: uses scripted turns when no LLM key is available
    (same behavior as the original demo)
"""
import asyncio
import random
import time
from dataclasses import asdict
from typing import AsyncIterator
import re

from .agents import (
    NegotiationState, build_arbiter_prompt, build_rep_prompt,
    detect_outcome, arbiter_initial_line,
)
from . import llm


# A transcript "event" is a dict:
# {"type": "message"|"hold"|"thinking"|"deal"|"error", ...}


def _format_history(state: NegotiationState, for_arbiter: bool) -> str:
    """Render conversation history for the LLM prompt."""
    out = []
    for m in state.messages:
        if m["role"] == "ai":
            out.append(f"Arbiter (you): {m['text']}")
        elif m["role"] in ("rep", "rep2"):
            label = "Retention Rep" if state.transfer_happened else "Frontline Rep"
            out.append(f"{label}: {m['text']}")
        elif m["role"] == "hold":
            out.append("[Hold music]")
    return "\n".join(out[-8:])  # last 8 turns for context


def _clean_llm(text: str) -> str:
    """Strip [bracketed commands] from text the audience will hear."""
    return re.sub(r"\[(?:TRANSFER TO RETENTION|DEAL REACHED)\]\s*", "", text).strip()


async def run_simulated_negotiation(
    customer_name: str,
    provider: str,
    current_rate: float,
    competitors: list[str] | None = None,
    tenure: int = 6,
    discount_range: tuple[float, float] = (0.20, 0.38),
    customer_phone_last4: str = "4571",
) -> AsyncIterator[dict]:
    """
    Run a full simulated negotiation and yield events.

    discount_range: (min_discount_fraction, max_discount_fraction) e.g. (0.25, 0.40) for 25-40% off.
    """
    min_disc, max_disc = discount_range
    target_rate = round(current_rate * (1 - max_disc), 2)     # aim for max
    walk_away = round(current_rate * (1 - min_disc - 0.05), 2)  # accept up to (min+5%) off

    state = NegotiationState(
        customer_name=customer_name,
        provider=provider,
        current_rate=current_rate,
        target_rate=target_rate,
        walk_away_rate=walk_away,
        competitors=competitors or [],
        tenure=tenure,
    )
    # Attach discount range for scripted fallbacks
    state._min_disc = min_disc
    state._max_disc = max_disc

    use_llm = llm.has_llm()

    yield {"type": "call_start", "provider": provider, "customer": customer_name}
    await asyncio.sleep(0.6)

    # 1. Arbiter greets
    opening = arbiter_initial_line(state)
    state.messages.append({"role": "ai", "text": opening})
    yield {"type": "message", "role": "ai", "text": opening}
    await asyncio.sleep(_speech_time(opening))

    # 2. Rep greeting (if using LLM, generate it; otherwise use scripted)
    if use_llm:
        try:
            rep_hi = llm.generate(
                build_rep_prompt(state),
                f"The call just connected. The Arbiter said:\n\n\"{opening}\"\n\nRespond as the frontline rep, greeting them and asking how you can help. Keep it under 2 sentences. Do NOT include [TRANSFER] or [DEAL] tags. Just your line of dialogue.",
                temperature=0.8,
            )
        except Exception as e:
            rep_hi = f"Thanks for calling {provider}, my name is {_rep_name()}. How can I help you today?"
    else:
        rep_hi = f"Thanks for calling {provider}, my name is {_rep_name()}. How can I help you today?"

    rep_hi = _clean_llm(rep_hi)
    state.messages.append({"role": "rep", "text": rep_hi})
    yield {"type": "message", "role": "rep", "text": rep_hi}
    await asyncio.sleep(_speech_time(rep_hi))

    # 3. Turn-by-turn loop
    max_turns = 14
    max_turn_after_transfer = 8
    post_transfer_turns = 0
    arbiter_post_msgs = 0  # how many things Arbiter has said post-transfer

    for turn in range(max_turns):
        # Arbiter's turn
        yield {"type": "thinking", "role": "ai"}
        if use_llm:
            try:
                history = _format_history(state, for_arbiter=True)
                sys_prompt = build_arbiter_prompt(state)
                user_msg = (
                    f"Conversation so far:\n{history}\n\n"
                    f"It's your turn to speak next. Respond to the rep. "
                    f"Keep it to 1-3 sentences, natural phone conversation. "
                    f"If you're ready to accept the rate offered and it's at or below ${walk_away}/month, "
                    f"say so clearly and confirm terms (duration, no new contract, email confirmation). "
                    f"If the rate is still too high, push back. If they refuse to budge, ask for retention/cancellations."
                )
                arbiter_text = llm.generate(sys_prompt, user_msg, temperature=0.7)
            except Exception as e:
                arbiter_text = _scripted_arbiter_line(state, turn, arbiter_post_msgs if state.transfer_happened else state.turns)
        else:
            arbiter_text = _scripted_arbiter_line(state, turn, arbiter_post_msgs if state.transfer_happened else state.turns)

        arbiter_text = _clean_llm(arbiter_text)
        if not arbiter_text:
            arbiter_text = "I appreciate that, but I need a better rate to keep the account."
        state.messages.append({"role": "ai", "text": arbiter_text})
        yield {"type": "message", "role": "ai", "text": arbiter_text}
        await asyncio.sleep(_speech_time(arbiter_text))
        if state.transfer_happened:
            arbiter_post_msgs += 1

        # Check if Arbiter is accepting/closing
        arbiter_accepting = any(w in arbiter_text.lower() for w in ["that works", "i'll take it", "that's acceptable", "lock it in", "great, thank", "that sounds good", "we'll stay"])

        # Rep's turn
        if use_llm:
            yield {"type": "thinking", "role": "rep" if not state.transfer_happened else "rep2"}
            history = _format_history(state, for_arbiter=False)
            sys_prompt = build_rep_prompt(state)
            if not state.transfer_happened:
                user_msg = (
                    f"Conversation so far:\n{history}\n\n"
                    f"It's your turn to respond. You are the frontline support rep. "
                    f"Remember you can only offer up to $10 off without transferring. "
                    f"If the caller is firm and mentions competitors/canceling, start your response with [TRANSFER TO RETENTION] and say you'll transfer them. "
                    f"If a deal is agreed, start with [DEAL REACHED]. Keep it 1-3 sentences."
                )
            else:
                user_msg = (
                    f"Conversation so far:\n{history}\n\n"
                    f"It's your turn as the RETENTION rep now. "
                    f"You can offer up to ~35% off (around ${round(current_rate*0.35,2)}/month discount). "
                    f"Start medium and only go to max if they push. "
                    f"If you reach a final agreed rate, start your response with [DEAL REACHED] and state the exact new monthly rate, duration (12 months), no new contract, and that you'll email confirmation. "
                    f"Keep it 1-3 sentences."
                )
            try:
                rep_text = llm.generate(sys_prompt, user_msg, temperature=0.8)
            except Exception:
                rep_text = _scripted_rep_line(state, turn, post_transfer_turns)
        else:
            rep_text = _scripted_rep_line(state, turn, post_transfer_turns)

        # Check for special actions
        outcome = detect_outcome(rep_text, state)
        clean_rep = _clean_llm(rep_text)

        if outcome["transfer"] and not state.transfer_happened:
            state.transfer_happened = True
            # Rep says their transfer line first
            transfer_line = clean_rep if clean_rep else "Let me transfer you to Retention, one moment please."
            state.messages.append({"role": "rep", "text": transfer_line})
            yield {"type": "message", "role": "rep", "text": transfer_line}
            await asyncio.sleep(_speech_time(transfer_line))
            # Hold music
            hold_duration = outcome["hold_duration"]
            yield {"type": "hold", "seconds": hold_duration}
            state.hold_seconds += hold_duration
            await asyncio.sleep(1.0)  # hold indicated, compressed for demo
            # New rep (retention) picks up
            ret_greeting = f"This is {_rep_name()} in Retention, I see we're looking at pricing. How can I help?"
            if use_llm:
                try:
                    ret_greeting = llm.generate(
                        build_rep_prompt(state).replace("FRONTLINE support team, NOT retention", "RETENTION specialist"),
                        "You just picked up a transferred call from a customer whose AI assistant is calling about their bill rate. Greet them briefly as a Retention rep. One sentence.",
                        temperature=0.8,
                    )
                    ret_greeting = _clean_llm(ret_greeting)
                except Exception:
                    pass
            state.messages.append({"role": "rep2", "text": ret_greeting})
            yield {"type": "message", "role": "rep2", "text": ret_greeting}
            await asyncio.sleep(_speech_time(ret_greeting))
            post_transfer_turns = 0
            arbiter_post_msgs = 0
            continue

        if outcome["deal"] or (arbiter_accepting and (state.turns + post_transfer_turns) > 4):
            # Deal reached
            final_rate = outcome.get("final_rate") or round(current_rate * random.uniform(0.62, 0.75), 2)
            final_rate = max(final_rate, round(current_rate * 0.55, 2))  # don't go lower than 45% off
            state.final_rate = final_rate
            state.deal_reached = True

            closing = clean_rep if clean_rep else f"I can lock that in at ${final_rate}/month for 12 months, no new contract, and I'll send a confirmation email."
            role = "rep2" if state.transfer_happened else "rep"
            state.messages.append({"role": role, "text": closing})
            yield {"type": "message", "role": role, "text": closing}
            await asyncio.sleep(_speech_time(closing))
            break

        # Normal rep response
        role = "rep2" if state.transfer_happened else "rep"
        state.messages.append({"role": role, "text": clean_rep})
        yield {"type": "message", "role": role, "text": clean_rep}
        await asyncio.sleep(_speech_time(clean_rep))

        if state.transfer_happened:
            post_transfer_turns += 1
            if post_transfer_turns >= max_turn_after_transfer:
                break
        state.turns += 1

    # 4. Arbiter closing
    if state.final_rate:
        closing = "Great, we'll stay. Thank you for your help — have a good day."
        state.messages.append({"role": "ai", "text": closing})
        yield {"type": "message", "role": "ai", "text": closing}
        await asyncio.sleep(_speech_time(closing))

    # 5. Summary
    annual_savings = round((state.current_rate - (state.final_rate or state.walk_away_rate)) * 12, 2)
    our_fee = round(annual_savings * 0.25, 2)
    user_keeps = round(annual_savings - our_fee, 2)
    final_rate = state.final_rate or round(state.current_rate * 0.7, 2)

    summary = (
        f"Negotiation complete. New rate: ${final_rate}/month "
        f"(was ${state.current_rate}). Annual savings: ${annual_savings}. "
        f"Arbiter's fee (25%): ${our_fee}. You keep: ${user_keeps}."
    )
    yield {
        "type": "deal",
        "text": summary,
        "old_rate": state.current_rate,
        "new_rate": final_rate,
        "annual_savings": annual_savings,
        "our_fee": our_fee,
        "user_keeps": user_keeps,
    }


# ---------- Helpers ----------

def _rep_name():
    return random.choice([
        "Brittany", "Ashley", "Marcus", "David", "Jordan", "Tasha",
        "Megan", "Ryan", "Tyler", "Sarah", "Chris", "Jessica", "Mike", "Lauren"
    ])


def _speech_time(text: str) -> float:
    """Delay between yielding subsequent messages to the client.

    The client queues TTS calls and plays them sequentially, so the audio
    naturally paces itself. We just need a small cadence so the UI doesn't
    flood and the "thinking" indicator reads naturally.
    """
    return 0.4


def _scripted_arbiter_line(state: NegotiationState, turn: int, post_transfer_turns: int) -> str:
    """Fallback scripted Arbiter lines when no LLM key is set."""
    # Before transfer: navigate from greeting to retention
    if not state.transfer_happened:
        if state.turns == 0:
            return f"Thank you — I'm reviewing their bill. I see they've been on the plan for {state.tenure} years, always on autopay with zero late payments, but their rate has crept up to ${state.current_rate}. I noticed new customers in the same zip are paying closer to $55-$65. Can we get them onto a comparable rate?"
        if state.turns == 1:
            return "I appreciate that, but $10 doesn't close the gap with the new-customer pricing. Competitors like Verizon Fios and T-Mobile are offering $49-55/month right now. My client would prefer to stay with you but is prepared to switch today if we can't reach something closer. Can you transfer me to your Retention or Cancellations team?"
        return "I'd like to speak with Retention please."
    # After transfer: post_transfer_turns counts arbiter-side messages already sent post-transfer
    if post_transfer_turns == 0:
        return f"Thanks for taking the call. To keep this customer today I'm looking for $25-35/month off plus the equipment fee waived — that gets us close to the new-customer rate and avoids a switch. What can you do?"
    if post_transfer_turns == 1:
        return "That's a meaningful step. Can you take another $10-15 off and waive the equipment fee? If we can get to the low $70s with no new contract and email confirmation today, we'll stay."
    return "That works for me. Can you confirm there's no new contract term, this is locked for 12 months, and you'll send a confirmation email to the account? Perfect — we'll stay. Thank you for your help."


def _scripted_rep_line(state: NegotiationState, turn: int, post_transfer_turns: int) -> str:
    """Fallback scripted rep lines. Discounts vary to feel realistic."""
    import random
    # Final discount varies within the provider's realistic range
    if not hasattr(state, '_scripted_final_discount'):
        state._scripted_final_discount = random.uniform(state._min_disc + 0.02, state._max_disc)
    final_discount = state._scripted_final_discount
    final_rate = round(state.current_rate * (1 - final_discount), 2)

    if state.turns == 0:
        return "Let me look at the account... I see the current plan. I can offer $10 off for the next 6 months as a loyalty discount."
    if state.turns == 1 and not state.transfer_happened:
        return "[TRANSFER TO RETENTION] I don't have access to those rates from my end, let me transfer you to Retention."
    if state.transfer_happened and post_transfer_turns == 0:
        mid_off_pct = (state._min_disc + state._max_disc) / 2 - 0.08
        mid_off = round(state.current_rate * mid_off_pct, 2)
        return f"I can offer ${mid_off} off a month for 12 months plus a free streaming bundle."
    return f"[DEAL REACHED] Alright, I can do ${round(state.current_rate - final_rate,2)} off for 12 months and remove the equipment fee. That brings it to ${final_rate}/month, no new contract, confirmation email will go out tonight."
