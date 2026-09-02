from typing import Dict, Tuple
from src.models import Mandate, Order, AgentAction

def check_within_cap(order: Order, mandate: Mandate) -> bool:
    return order.amount <= mandate.spending_cap_amount

def check_mandate_active(order: Order, mandate: Mandate) -> bool:
    return mandate.status == 'active' and mandate.valid_from <= order.placed_at <= mandate.valid_until

def check_merchant_matches(order: Order, mandate: Mandate) -> bool:
    return order.merchant_id == mandate.merchant_id

def check_fulfilled(order: Order) -> bool:
    return order.status == 'fulfilled' and order.fulfilled_at is not None

def check_timestamps_consistent(order: Order, confirming_action: AgentAction) -> bool:
    if order.fulfilled_at is not None and order.fulfilled_at < order.placed_at:
        return False
    if confirming_action.timestamp > order.placed_at:
        return False
    return True

def evaluate_confidence(order: Order, mandate: Mandate, confirming_action: AgentAction) -> Tuple[float, Dict[str, bool]]:
    checks = {
        "within_cap": check_within_cap(order, mandate),
        "mandate_active": check_mandate_active(order, mandate),
        "merchant_matches": check_merchant_matches(order, mandate),
        "fulfilled": check_fulfilled(order),
        "timestamps_consistent": check_timestamps_consistent(order, confirming_action)
    }
    
    passed_count = sum(1 for passed in checks.values() if passed)
    confidence_score = passed_count / len(checks)
    
    return confidence_score, checks
