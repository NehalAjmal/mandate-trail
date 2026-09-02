from dataclasses import dataclass
from typing import Optional


@dataclass
class Mandate:
    id: str
    user_id: str
    agent_id: str
    merchant_id: str
    spending_cap_amount: int  # paise
    spending_cap_currency: str
    valid_from: int
    valid_until: int
    status: str
    created_at: int


@dataclass
class AgentAction:
    id: str
    mandate_id: str
    action_type: str
    merchant_id: str
    item_description: str
    amount: int  # paise
    currency: str
    timestamp: int
    raw_payload: str  # JSON string


@dataclass
class Order:
    id: str
    mandate_id: str
    confirming_action_id: str
    merchant_id: str
    amount: int  # paise
    currency: str
    status: str
    placed_at: int
    fulfilled_at: Optional[int]


@dataclass
class Dispute:
    id: str
    order_id: str
    payment_id: str
    amount: int  # paise
    currency: str
    amount_deducted: int
    reason_code: str
    phase: str
    status: str
    respond_by: int
    raised_at: int
    ground_truth_label: str
    is_held_out: bool


@dataclass
class EvidencePacket:
    id: str
    dispute_id: str
    narrative_text: str
    grounding_check_passed: bool
    mapped_evidence_fields: str  # JSON string
    generated_at: int


@dataclass
class Decision:
    id: str
    dispute_id: str
    confidence_score: float
    checks_passed: str  # JSON string
    recommended_action: str
    decided_at: int
    decided_by: str


@dataclass
class AuditLogEntry:
    id: int
    dispute_id: str
    event_type: str
    event_payload: str  # JSON string
    created_at: int
