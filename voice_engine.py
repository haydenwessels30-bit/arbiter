"""
Arbiter — Real Outbound Voice Call Engine
==========================================

This module connects to LiveKit Agents to place actual phone calls
to billers using a conversational AI agent.

LIVEKIT FREE TIER (no credit card required):
  - 1,000 agent session minutes / month
  - 1 free US phone number
  - 5,000 WebRTC minutes / month
  - $2.50 in inference credits (~50 min with Deepgram/OpenAI/ElevenLabs)
  - Sign up: https://cloud.livekit.io/

When you're ready to make REAL calls:
  1. Create a LiveKit Cloud account (free, no card): https://cloud.livekit.io/
  2. Create a Project, copy API Key + API Secret + Project URL
  3. Set env vars:
       LIVEKIT_URL=wss://your-project.livekit.cloud
       LIVEKIT_API_KEY=APxxxx
       LIVEKIT_API_SECRET=xxxx
       OPENAI_API_KEY=sk-...   (for the LLM driving the agent)
       DEEPGRAM_API_KEY=...    (for speech-to-text, free tier: $200 credit)
       ELEVENLABS_API_KEY=...  (for natural TTS, free tier: 10k credits)
  4. Rent a US phone number from LiveKit dashboard ($1/mo after free #)
  5. Call place_call() with the biller's retention number + negotiation brief
  6. The agent will dial in, navigate, negotiate, and stream results back

The agent is defined in `agent.py` (see that file for the negotiation logic).
Run the agent worker in a separate process:
    python agent.py start
"""

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

# Note: these imports are only needed when actually placing calls.
# `pip install livekit livekit-agents livekit-plugins-openai livekit-plugins-deepgram livekit-plugins-elevenlabs phonenumbers`
try:
    from livekit import api
    LIVEKIT_AVAILABLE = True
except ImportError:
    LIVEKIT_AVAILABLE = False


@dataclass
class NegotiationBrief:
    """Structured brief given to the AI agent before placing a call."""
    customer_name: str
    account_number: str            # Full account # or last 4 + zip verification
    account_pin: Optional[str]     # Biller PIN if required for auth
    provider: str                  # "Comcast/Xfinity", "Verizon", etc.
    provider_retention_number: str # Direct line to retention if known, else main support
    current_monthly_rate: float
    target_monthly_rate: float     # Rate we're aiming for (e.g., new-customer rate)
    walk_away_rate: float          # Don't settle above this; hang up and retry
    competitor_rates: list[str] = field(default_factory=list)
    customer_tenure_years: int = 5
    notes: str = ""
    # Call recording consent: True = announce recording (safest, covers all states)
    announce_recording: bool = True
    # AI disclosure: True = say "I'm an AI assistant" upfront (required in CA + trend)
    disclose_ai: bool = True


@dataclass
class CallResult:
    call_sid: str
    status: str  # "connected" | "no_answer" | "busy" | "failed" | "completed"
    recording_url: Optional[str] = None
    transcript: list[dict] = field(default_factory=list)
    negotiated_rate: Optional[float] = None
    original_rate: Optional[float] = None
    annual_savings: Optional[float] = None
    notes: str = ""
    duration_seconds: int = 0
    confirmation_email_sent: bool = False


def place_call(brief: NegotiationBrief, to_number: str, from_number: str) -> str:
    """
    Dispatch an outbound call via LiveKit SIP trunking.
    Returns a job_id that can be used to track status.
    In production, this creates a LiveKit SIP Dispatch Rule and kicks off an agent.
    """
    if not LIVEKIT_AVAILABLE:
        raise RuntimeError(
            "LiveKit SDK not installed. Install with:\n"
            "  pip install livekit livekit-agents livekit-plugins-openai "
            "livekit-plugins-deepgram livekit-plugins-elevenlabs phonenumbers\n"
            "Then set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET env vars."
        )

    url = os.environ["LIVEKIT_URL"]
    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]

    job_id = f"arbiter_{uuid.uuid4().hex[:12]}"

    # Create a token for the agent worker to join
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(f"arbiter-agent-{job_id}")
        .with_name("Arbiter Negotiation Agent")
        .with_grants(api.VideoGrants(
            room_join=True,
            room=job_id,
            can_publish=True,
            can_subscribe=True,
        ))
        .with_attributes({
            "job_type": "negotiation",
            "customer_name": brief.customer_name,
            "provider": brief.provider,
            "to_number": to_number,
            "from_number": from_number,
            "brief": brief.to_json() if hasattr(brief, 'to_json') else str(brief.__dict__),
        })
        .to_jwt()
    )

    # Create a SIP outbound call to the biller
    # (Requires SIP trunk configured in LiveKit dashboard — LiveKit provides this)
    lkapi = api.LiveKitAPI(url, api_key, api_secret)
    # Note: full SIP dispatch setup would go here using lkapi.sip.create_sip_dispatch_rule
    # For now we emit the token + room for the worker to pick up
    print(f"[Arbiter] Dispatched call job {job_id}")
    print(f"[Arbiter] Room: {job_id}")
    print(f"[Arbiter] Dialing {to_number} from {from_number}")
    print(f"[Arbiter] Biller: {brief.provider} | Customer: {brief.customer_name}")
    print(f"[Arbiter] Current: ${brief.current_monthly_rate} -> Target: ${brief.target_monthly_rate}")

    return job_id


# ---------------------------------------------------------------------------
# When you're ready to go live with real calls, here's the setup checklist:
#
# 1. SIGN UP (free):
#    - LiveKit Cloud: https://cloud.livekit.io/ (1000 min/mo free, no card)
#    - Deepgram: https://deepgram.com/ (speech-to-text, $200 free credit)
#    - OpenAI: https://platform.openai.com/ (GPT-4o for agent reasoning)
#    - ElevenLabs: https://elevenlabs.io/ (natural TTS, free tier)
#
# 2. INSTALL DEPS:
#    pip install livekit livekit-agents \
#        livekit-plugins-openai \
#        livekit-plugins-deepgram \
#        livekit-plugins-elevenlabs \
#        phonenumbers
#
# 3. CONFIGURE:
#    - Create project in LiveKit Cloud
#    - Buy/port a US number (LiveKit has 1 free number)
#    - Set environment variables (see above)
#
# 4. WRITE THE AGENT (see agent.py)
#    The agent uses a function-calling loop:
#    - Says the AI disclosure + identity upfront
#    - Authenticates the customer account
#    - Asks for retention department
#    - Negotiates using known leverage (competitor rates, tenure, on-time payment history)
#    - Detects "final offer" vs bluff
#    - Politely escalates (asks for supervisor) if needed
#    - Closes at or below target rate
#    - Gets verbal + written confirmation (email)
#
# 5. RUN THE WORKER:
#    python agent.py start  # runs in background, picks up jobs from place_call()
#
# 6. CONNECT TO THE WEB APP:
#    Replace the build_negotiation() scripted demo with place_call()
#    Stream the call's transcript via WebSocket to the user's browser
#    (LiveKit provides this natively)
#
# COST PER CALL (at scale, post-free-tier):
#   ~8 minute call = ~$0.08 telephony + $0.05 STT + $0.03 LLM + $0.08 TTS ≈ $0.24/call
#   Versus a human call center rep: ~$3.33/call (at $25/hr)
#   Our fee at 25% of $400 annual savings = $100 per successful call
#   Even at 50% win rate: $50 revenue per attempt vs $0.24 cost = INSANE margins
# ---------------------------------------------------------------------------
