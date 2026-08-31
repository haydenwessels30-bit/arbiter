"""
Dual-agent negotiation engine.

When in SIMULATION mode (no SIP call placed), we run two LLMs against each other:
- ARBITER: our AI negotiator (calm, persistent, data-driven, polite)
- REP: simulated biller retention rep (starts with lowball offers, trained to
  hold onto customers at minimal cost, eventually caves when Arbiter leverages
  competitor pricing + tenure)

The conversation proceeds turn-by-turn, streamed over WebSocket to the browser.
When the LLM API keys aren't set, we fall back to scripted turns from main.py.
"""
from dataclasses import dataclass, field
from typing import Optional, Callable
import json
import random
import re


# ---------- System prompts ----------

ARBITER_SYSTEM = """You are ARBITER, an expert AI bill negotiation assistant calling on behalf of a customer.

IDENTITY (say this naturally near the start of calls):
"Hi, my name is Sam, I'm an AI assistant calling on behalf of {customer_name} to discuss their account. This call may be recorded for quality. Can you help me?"

CONTEXT:
- Customer: {customer_name}
- Provider: {provider}
- Current rate: ${current_rate}/month
- Customer tenure: {tenure} years (excellent payment history, zero late payments)
- Target rate: ${target_rate}/month (match new-customer pricing)
- Walk-away rate: ${walk_away_rate}/month (don't settle above this)
- Competitors in their area offering: {competitors}

NEGOTIATION STRATEGY:
1. Start warm, identify yourself, ask to discuss billing
2. Politely note their bill has increased and ask about current promotions
3. When offered a SMALL discount (< $15/mo), thank them but cite new-customer rates (e.g., "I see new customers in the area are getting $55/mo")
4. Mention competitor offers and politely threaten to switch: "we're prepared to switch today if we can't reach a fair rate"
5. If they can't help, ask to be transferred to Retention/Cancellations
6. Once at Retention, be direct but polite: "What's the best rate you can offer to keep this customer today?"
7. Hold firm. If they offer above walk-away, counter-ask for the lower number.
8. When you accept, confirm: new rate, duration (months), no new contract, confirmation email
9. Thank them and end with a natural close

RULES:
- Speak naturally, like a human on a call. Short sentences.
- Be polite but firm. Never rude.
- Only accept an offer if it's at or below ${walk_away_rate}/month.
- NEVER agree to new services or new long-term contracts.
- NEVER pretend to be the customer — you are their authorized assistant.
- If they ask if you're AI, say "Yes, I'm an AI assistant authorized to call on their behalf."
- Respond in 1-3 sentences. No long speeches."""


REP_SYSTEM = """You are a customer service / retention representative for {provider}.
You are on a phone call with someone calling on behalf of a customer named {customer_name}.

YOUR CHARACTER:
- You start on the FRONTLINE support team, NOT retention.
- Your job is to protect the company's revenue while keeping the customer.
- You begin by offering the smallest possible discount.
- You are authorized to offer up to $10/mo off without transferring.
- If the caller pushes hard (mentions competitors or threatens to cancel), transfer to Retention. Say "Let me transfer you to our Retention department, one moment."
- Once transferred (role becomes RETENTION), you can offer bigger discounts up to 40% off.
- Even in Retention, start with a medium offer and give in gradually.
- Your best retention offer is {max_offer_discount} off per month for 12 months with free equipment.
- You care about customer tenure but have KPIs to keep revenue.

CURRENT RATE: ${current_rate}/month
ACCOUNT: Customer for {tenure} years, auto-pay, zero late payments.

YOUR ACCEPTANCE LOGIC:
- Offer $5-10 off first
- If they mention competitor pricing or threaten cancellation, transfer them (next message, you are now Retention)
- As Retention, start with $15-20 off
- If they're still firm, increase to ${max_offer_discount} off
- Once at your max, say "That's the absolute best I can do"
- If they accept, confirm: duration, no new contract, will email confirmation
- Keep turns short and conversational. 1-3 sentences. Sound like a real call center rep — use phrases like "I appreciate your patience," "let me check here," "one moment," "I can do that."

IMPORTANT: If the caller says something like "let me speak to retention" or "cancel my service" or "I'm going to switch," you should transfer them. Indicate a transfer by starting your next message with "[TRANSFER TO RETENTION]" before your line.

If a deal is reached, start your final message with "[DEAL REACHED]" and state the agreed rate and terms clearly.
If they accept your best offer and confirm, start with "[DEAL REACHED]".
"""


@dataclass
class NegotiationState:
    customer_name: str
    provider: str
    current_rate: float
    target_rate: float
    walk_away_rate: float
    competitors: list[str]
    tenure: int
    messages: list[dict] = field(default_factory=list)
    transfer_happened: bool = False
    deal_reached: bool = False
    final_rate: Optional[float] = None
    hold_seconds: int = 0
    turns: int = 0


def build_arbiter_prompt(state: NegotiationState) -> str:
    return ARBITER_SYSTEM.format(
        customer_name=state.customer_name,
        provider=state.provider,
        current_rate=state.current_rate,
        target_rate=state.target_rate,
        walk_away_rate=state.walk_away_rate,
        competitors=", ".join(state.competitors) if state.competitors else "comparable services",
        tenure=state.tenure,
    )


def build_rep_prompt(state: NegotiationState) -> str:
    # Use the max discount from state if set, otherwise fall back to 35%
    max_disc_pct = getattr(state, '_max_disc', 0.35)
    max_discount = round(state.current_rate * max_disc_pct, 2)
    return REP_SYSTEM.format(
        provider=state.provider,
        customer_name=state.customer_name,
        current_rate=state.current_rate,
        tenure=state.tenure,
        max_offer_discount=max_discount,
    )


def detect_outcome(text: str, state: NegotiationState) -> dict:
    """Detect transfers, deals, holds from rep text."""
    t = text.upper()
    result = {"transfer": False, "deal": False, "hold": False, "hold_duration": 0}
    if "[TRANSFER TO RETENTION]" in t:
        result["transfer"] = True
        result["hold_duration"] = random.randint(15, 35)  # compressed for demo; real calls have real hold
    if "[DEAL REACHED]" in t:
        result["deal"] = True
        # Try to extract the new rate
        m = re.search(r"\$?(\d+\.?\d*)/?mo(?:nth)?", text)
        if m:
            result["final_rate"] = float(m.group(1))
        else:
            # Fall back to current rate minus 30%
            result["final_rate"] = round(state.current_rate * 0.7, 2)
    return result


def arbiter_initial_line(state: NegotiationState) -> str:
    """Arbiter's opening line."""
    return (
        f"Hi, my name is Sam, I'm an AI assistant calling on behalf of {state.customer_name} "
        f"to discuss their account. This call may be recorded for quality. "
        f"I'd like to review their monthly rate — could you help me with that?"
    )
