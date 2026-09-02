import os
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
    Do not invent any details, device fingerprints, IP addresses, or customer names.
    This was an agent-initiated transaction, so do not claim a human user clicked or typed anything.
    
    FACTS:
    {facts}
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=prompt
            )
            return response.text
        except APIError as e:
            if e.code == 429:
                time.sleep(15)  # Wait and retry for quota limits
            else:
                raise
    raise Exception("Exceeded max retries for draft_narrative due to API rate limits.")

def perform_grounding_check(narrative: str, mandate: Mandate, actions: List[AgentAction], order: Order, dispute: Dispute) -> Tuple[bool, str]:
    import time
    from google.genai.errors import APIError
    facts = _build_facts_string(mandate, actions, order, dispute)
    
    check_prompt = f"""
    You are an auditor. Read the following Narrative and the Source Facts.
    If the Narrative contains ANY specific claim, amount, date, time, or named entity that is NOT explicitly present in the Source Facts, you must reject it.
    If it mentions device fingerprints, IP addresses, human user actions, or anything implying a human clicked it, reject it (because it was an AI agent).
    
    Source Facts:
    {facts}
    
    Narrative:
    {narrative}
    
    Respond in JSON format:
    {{"passed": true/false, "reason": "short explanation of what failed, or 'clean' if passed"}}
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    response = None
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=check_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            break
        except APIError as e:
            if e.code == 429:
                time.sleep(15)
            else:
                raise
    
    if not response:
        return False, "Exceeded max retries for grounding check due to API rate limits."
    
    try:
        result = json.loads(response.text)
        return result.get('passed', False), result.get('reason', 'Failed to parse JSON')
    except Exception as e:
        # If it fails to parse, we default to failing the grounding check to be safe.
        return False, f"Grounding check failed to parse response: {str(e)}"
