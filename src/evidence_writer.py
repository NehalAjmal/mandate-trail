import os
import re
import json
from typing import List, Tuple
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

from src.models import Mandate, AgentAction, Order, Dispute

def _format_timestamp(ts: int) -> str:
    from datetime import datetime, timezone
    if ts is None: return "None"
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def _format_amount(paise: int) -> str:
    return f"{paise / 100:.2f}"

def _build_facts_string(mandate: Mandate, actions: List[AgentAction], order: Order, dispute: Dispute) -> str:
    facts = f"Mandate ID: {mandate.id}\n"
    facts += f"Merchant: {mandate.merchant_id}\n"
    facts += f"Cap: INR {_format_amount(mandate.spending_cap_amount)}\n"
    facts += f"Valid From: {_format_timestamp(mandate.valid_from)}\n"
    facts += f"Valid Until: {_format_timestamp(mandate.valid_until)}\n"

    facts += f"\nOrder ID: {order.id}\n"
    facts += f"Order Amount: INR {_format_amount(order.amount)}\n"
    facts += f"Placed At: {_format_timestamp(order.placed_at)}\n"
    facts += f"Fulfilled At: {_format_timestamp(order.fulfilled_at)}\n"

    facts += f"\nDispute Reason: {dispute.reason_code}\n"
    facts += "\nAgent Actions (Chronological):\n"
    for a in actions:
        facts += f"- {_format_timestamp(a.timestamp)}: {a.action_type} - {a.item_description} (INR {_format_amount(a.amount)})\n"
    return facts

def draft_narrative(mandate: Mandate, actions: List[AgentAction], order: Order, dispute: Dispute) -> str:
    import time
    from google.genai.errors import APIError
    facts = _build_facts_string(mandate, actions, order, dispute)

    prompt = f"""
    You are an agent acting on behalf of a merchant defending against a chargeback.
    Write a brief explanation letter (evidence summary) based ONLY on the following facts.

    CRITICAL INSTRUCTIONS:
    1. Do not invent any details, device fingerprints, IP addresses, or customer names.
    2. This was an agent-initiated transaction, so do not claim a human user clicked, logged in, or typed anything.
    3. Do not mention any browsers (safari, chrome, firefox, edge) or devices (iphone, android, phone).
    4. Do not include any numbers, amounts, or prices that are not explicitly listed in the FACTS below.

    FACTS:
    {facts}
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini").strip()

    if provider == "groq":
        import openai
        client = openai.OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY")
        )
        for attempt in range(50):
            try:
                response = client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Groq API returned {e}, retrying after 15s... (Attempt {attempt+1}/50)")
                time.sleep(15)
        raise Exception("Exceeded max retries for draft_narrative via Groq.")
    else:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
        for attempt in range(50):
            try:
                response = client.models.generate_content(
                    model='gemini-3.5-flash-lite',
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.0)
                )
                return "".join([p.text for p in response.candidates[0].content.parts if p.text])
            except APIError as e:
                if e.code in (429, 503):
                    print(f"Gemini API returned {e.code}, retrying after 15s... (Attempt {attempt+1}/50)")
                    time.sleep(15)  # Wait and retry for quota or capacity limits
                else:
                    raise
        raise Exception("Exceeded max retries for draft_narrative due to API rate limits.")


# Phrases that can never legitimately appear in a narrative about an agent-initiated
# transaction -- their presence means the narrative invented a human interaction that
# didn't happen. Deliberately blunt and line-by-line auditable rather than "smart":
# the whole point of this function is that a person can read it top to bottom and know
# exactly what it checks, with no judgment delegated to another model.
FORBIDDEN_PHRASES = [
    "ip address", "device fingerprint", "clicked", "logged in", "typed",
    "browser", "safari", "chrome", "firefox", "edge browser",
    "iphone", "android", "their phone", "her phone", "his phone",
    "customer's device", "user's device",
]

_IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
_AMOUNT_PATTERN = re.compile(r"INR\s*([\d,]+\.\d{2})")


def perform_grounding_check(narrative: str, mandate: Mandate, actions: List[AgentAction], order: Order, dispute: Dispute) -> Tuple[bool, str]:
    """
    Deterministic grounding check -- no LLM call, no network call. Every claim in the
    narrative either matches the structured facts it was given, or the narrative is
    rejected. The contest/escalate decision in decision.py depends on this function's
    output, and that decision must never be made by a model.
    """
    lower = narrative.lower()

    for phrase in FORBIDDEN_PHRASES:
        if phrase in lower:
            return False, f"Narrative references '{phrase}', which cannot be true for an agent-initiated transaction"

    if _IP_PATTERN.search(narrative):
        return False, "Narrative contains an IP address, which agent-transaction evidence never includes"

    allowed_amounts = {
        f"{mandate.spending_cap_amount / 100:.2f}",
        f"{order.amount / 100:.2f}",
    }
    for a in actions:
        allowed_amounts.add(f"{a.amount / 100:.2f}")
    for amt in _AMOUNT_PATTERN.findall(narrative):
        if amt.replace(",", "") not in allowed_amounts:
            return False, f"Narrative cites INR {amt}, which doesn't match any amount in the structured facts"

    return True, "clean"
