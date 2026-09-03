# pyrefly: ignore [missing-import]
import pytest
from src.models import Mandate, AgentAction, Order, Dispute
from src.evidence_writer import perform_grounding_check, draft_narrative

@pytest.fixture
def mock_data():
    mandate = Mandate(id="m1", user_id="u1", agent_id="a1", merchant_id="zomato", spending_cap_amount=1000, spending_cap_currency="INR", valid_from=10, valid_until=20, status="active", created_at=5)
    action = AgentAction(id="a1", mandate_id="m1", action_type="pay", merchant_id="zomato", item_description="item", amount=100, currency="INR", timestamp=10, raw_payload="{}")
    order = Order(id="o1", mandate_id="m1", confirming_action_id="a1", merchant_id="zomato", amount=100, currency="INR", status="fulfilled", placed_at=15, fulfilled_at=20)
    dispute = Dispute(id="d1", order_id="o1", payment_id="p1", amount=100, currency="INR", amount_deducted=0, reason_code="fraud", phase="chargeback", status="open", respond_by=30, raised_at=25, ground_truth_label="contest", is_held_out=False)
    
    return mandate, [action], order, dispute

def test_grounding_check_pass(mock_data):
    mandate, actions, order, dispute = mock_data
    # Use only facts provided in the prompt
    narrative = "The mandate m1 authorized up to INR 10.00 at zomato. Order o1 was placed for INR 1.00."
    passed, reason = perform_grounding_check(narrative, mandate, actions, order, dispute)
    assert passed is True

def test_grounding_check_fail_invented_claim(mock_data):
    mandate, actions, order, dispute = mock_data
    # Deliberately invent device IP and a human click
    narrative = "The mandate m1 authorized up to INR 10.00 at zomato. The user clicked checkout from IP 192.168.1.1 on their iPhone."
    passed, reason = perform_grounding_check(narrative, mandate, actions, order, dispute)
    assert passed is False
    assert "clean" not in reason.lower()
