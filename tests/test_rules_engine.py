# pyrefly: ignore [missing-import]
import pytest
from src.models import Mandate, Order, AgentAction
from src.rules_engine import (
    check_within_cap,
    check_mandate_active,
    check_merchant_matches,
    check_fulfilled,
    check_timestamps_consistent,
    evaluate_confidence
)

def test_within_cap():
    mandate = Mandate(id="m1", user_id="u1", agent_id="a1", merchant_id="merch", spending_cap_amount=1000, spending_cap_currency="INR", valid_from=10, valid_until=20, status="active", created_at=5)
    order_pass = Order(id="o1", mandate_id="m1", confirming_action_id="a1", merchant_id="merch", amount=1000, currency="INR", status="placed", placed_at=15, fulfilled_at=None)
    order_fail = Order(id="o2", mandate_id="m1", confirming_action_id="a1", merchant_id="merch", amount=1001, currency="INR", status="placed", placed_at=15, fulfilled_at=None)
    
    assert check_within_cap(order_pass, mandate) is True
    assert check_within_cap(order_fail, mandate) is False

def test_mandate_active():
    mandate_active = Mandate(id="m1", user_id="u1", agent_id="a1", merchant_id="merch", spending_cap_amount=1000, spending_cap_currency="INR", valid_from=100, valid_until=200, status="active", created_at=90)
    mandate_expired = Mandate(id="m2", user_id="u1", agent_id="a1", merchant_id="merch", spending_cap_amount=1000, spending_cap_currency="INR", valid_from=100, valid_until=200, status="expired", created_at=90)
    
    order_valid = Order(id="o1", mandate_id="m1", confirming_action_id="a1", merchant_id="merch", amount=100, currency="INR", status="placed", placed_at=150, fulfilled_at=None)
    order_early = Order(id="o2", mandate_id="m1", confirming_action_id="a1", merchant_id="merch", amount=100, currency="INR", status="placed", placed_at=99, fulfilled_at=None)
    order_late = Order(id="o3", mandate_id="m1", confirming_action_id="a1", merchant_id="merch", amount=100, currency="INR", status="placed", placed_at=201, fulfilled_at=None)
    
    assert check_mandate_active(order_valid, mandate_active) is True
    assert check_mandate_active(order_valid, mandate_expired) is False
    assert check_mandate_active(order_early, mandate_active) is False
    assert check_mandate_active(order_late, mandate_active) is False

def test_merchant_matches():
    mandate = Mandate(id="m1", user_id="u1", agent_id="a1", merchant_id="zomato", spending_cap_amount=1000, spending_cap_currency="INR", valid_from=10, valid_until=20, status="active", created_at=5)
    order_pass = Order(id="o1", mandate_id="m1", confirming_action_id="a1", merchant_id="zomato", amount=100, currency="INR", status="placed", placed_at=15, fulfilled_at=None)
    order_fail = Order(id="o2", mandate_id="m1", confirming_action_id="a1", merchant_id="swiggy", amount=100, currency="INR", status="placed", placed_at=15, fulfilled_at=None)
    
    assert check_merchant_matches(order_pass, mandate) is True
    assert check_merchant_matches(order_fail, mandate) is False

def test_fulfilled():
    order_pass = Order(id="o1", mandate_id="m1", confirming_action_id="a1", merchant_id="zomato", amount=100, currency="INR", status="fulfilled", placed_at=15, fulfilled_at=20)
    order_fail_status = Order(id="o2", mandate_id="m1", confirming_action_id="a1", merchant_id="zomato", amount=100, currency="INR", status="placed", placed_at=15, fulfilled_at=20)
    order_fail_null = Order(id="o3", mandate_id="m1", confirming_action_id="a1", merchant_id="zomato", amount=100, currency="INR", status="fulfilled", placed_at=15, fulfilled_at=None)
    
    assert check_fulfilled(order_pass) is True
    assert check_fulfilled(order_fail_status) is False
    assert check_fulfilled(order_fail_null) is False

def test_timestamps_consistent():
    action = AgentAction(id="a1", mandate_id="m1", action_type="pay", merchant_id="merch", item_description="item", amount=100, currency="INR", timestamp=10, raw_payload="{}")
    order_pass = Order(id="o1", mandate_id="m1", confirming_action_id="a1", merchant_id="merch", amount=100, currency="INR", status="fulfilled", placed_at=15, fulfilled_at=20)
    order_fail_action = Order(id="o2", mandate_id="m1", confirming_action_id="a1", merchant_id="merch", amount=100, currency="INR", status="fulfilled", placed_at=5, fulfilled_at=20)
    order_fail_fulfill = Order(id="o3", mandate_id="m1", confirming_action_id="a1", merchant_id="merch", amount=100, currency="INR", status="fulfilled", placed_at=15, fulfilled_at=10)
    
    assert check_timestamps_consistent(order_pass, action) is True
    assert check_timestamps_consistent(order_fail_action, action) is False
    assert check_timestamps_consistent(order_fail_fulfill, action) is False

def test_evaluate_confidence():
    mandate = Mandate(id="m1", user_id="u1", agent_id="a1", merchant_id="zomato", spending_cap_amount=1000, spending_cap_currency="INR", valid_from=10, valid_until=20, status="active", created_at=5)
    action = AgentAction(id="a1", mandate_id="m1", action_type="pay", merchant_id="zomato", item_description="item", amount=100, currency="INR", timestamp=10, raw_payload="{}")
    order = Order(id="o1", mandate_id="m1", confirming_action_id="a1", merchant_id="zomato", amount=100, currency="INR", status="fulfilled", placed_at=15, fulfilled_at=20)
    
    score, checks = evaluate_confidence(order, mandate, action)
    assert score == 1.0
    assert all(checks.values())
    
    # Modify order to fail one check
    order_bad = Order(id="o2", mandate_id="m1", confirming_action_id="a1", merchant_id="swiggy", amount=100, currency="INR", status="fulfilled", placed_at=15, fulfilled_at=20)
    score, checks = evaluate_confidence(order_bad, mandate, action)
    assert score == 0.8
    assert checks["merchant_matches"] is False
    assert checks["within_cap"] is True
