from typing import Dict, Tuple, List
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

def check_no_duplicate_nearby(order: Order, sibling_orders: List[Order], window_seconds=3600) -> bool:
    """
    False if another order under the same mandate has a near-identical amount within
    `window_seconds` of this one -- a double-charge glitch or a genuinely ambiguous
    near-simultaneous re-order, either way something a human should look at rather
    than the system confidently contesting.
    """
    for other in sibling_orders:
        if other.id == order.id:
            continue
        if abs(other.amount - order.amount) <= 1 and abs(other.placed_at - order.placed_at) <= window_seconds:
            return False
    return True

def evaluate_confidence(order: Order, mandate: Mandate, confirming_action: AgentAction, sibling_orders: List[Order]) -> Tuple[float, Dict[str, bool]]:
    checks = {
        "within_cap": check_within_cap(order, mandate),
        "mandate_active": check_mandate_active(order, mandate),
        "merchant_matches": check_merchant_matches(order, mandate),
        "fulfilled": check_fulfilled(order),
        "timestamps_consistent": check_timestamps_consistent(order, confirming_action),
        "no_duplicate_nearby": check_no_duplicate_nearby(order, sibling_orders)
    }
    
    passed_count = sum(1 for passed in checks.values() if passed)
    confidence_score = passed_count / len(checks)
    
    return confidence_score, checks
