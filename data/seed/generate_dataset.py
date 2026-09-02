"""
Builds the 60-record synthetic dataset from scratch.
Fixed seed (AI_RULES.md rule 9) -- re-running this produces the identical DB every time.
"""
import json
import os
import random
import sys

# Allow running from repo root: python data/seed/generate_dataset.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.models import Mandate, AgentAction, Order, Dispute
from src import db

SEED = 20260901
random.seed(SEED)

# --- Shared constants ---

MERCHANTS = ['zomato', 'swiggy', 'zepto', 'blinkit', 'bigbasket']
REASON_CODES = [
    'goods_or_services_not_received_or_partially_received',
    'non_matching_account_number',
    'processed_invalid_expired_card',
]
ITEMS = [
    '2x paneer tikka, 1x butter naan',
    '1x chicken biryani, 1x raita',
    '3x masala dosa, 2x filter coffee',
    '1x margherita pizza, 1x garlic bread',
    '5x grocery essentials pack',
    '2x protein shake, 1x energy bar',
    '1x thali meal combo',
    '4x samosa, 2x chai',
]

# Base timestamp: 2026-08-01 00:00:00 UTC
BASE_TS = 1753920000
DAY = 86400


def _ts(day_offset, hour=12):
    return BASE_TS + day_offset * DAY + hour * 3600


def _paise(rupees):
    return rupees * 100


# Counters for globally unique IDs
_counters = {'mandate': 0, 'action': 0, 'order': 0, 'disp': 0}

def _next_id(prefix):
    _counters[prefix] += 1
    return f"{prefix}_{_counters[prefix]:04d}"


def _make_action_chain(mandate_id, merchant_id, amount, day_offset):
    """Generate the 4-step agent action sequence: search -> select -> confirm -> pay."""
    actions = []
    for i, atype in enumerate(['search', 'select', 'confirm', 'pay']):
        a = AgentAction(
            id=_next_id('action'),
            mandate_id=mandate_id,
            action_type=atype,
            merchant_id=merchant_id,
            item_description=random.choice(ITEMS),
            amount=amount,
            currency='INR',
            timestamp=_ts(day_offset, hour=10 + i),
            raw_payload=json.dumps({'step': i + 1, 'type': atype}),
        )
        actions.append(a)
    return actions


def _build_archetype(arch_num, count, held_out_count):
    """Generate records for one archetype. Returns list of (mandate, actions, order, dispute, is_held_out) tuples."""
    records = []

    # Decide which indices are held-out (deterministic from seed)
    held_out_indices = set(random.sample(range(count), held_out_count))

    for i in range(count):
        day_offset = arch_num * 4 + i
        merchant = random.choice(MERCHANTS)
        cap_rupees = random.choice([500, 1000, 1500, 2000])
        order_rupees = random.randint(100, cap_rupees - 50) if cap_rupees > 150 else 100

        mandate_id = _next_id('mandate')
        user_id = f"user_{random.randint(1, 30):03d}"

        # Defaults: clean legitimate (archetype 1). Other archetypes override below.
        mandate_status = 'active'
        mandate_valid_from = _ts(day_offset - 30)
        mandate_valid_until = _ts(day_offset + 30)
        order_merchant = merchant
        order_amount = _paise(order_rupees)
        order_status = 'fulfilled'
        placed_at = _ts(day_offset, hour=13)
        fulfilled_at = _ts(day_offset, hour=15)
        reason_code = random.choice(REASON_CODES)
        ground_truth = 'contest'

        if arch_num == 2:
            # Cap exceeded
            order_amount = _paise(cap_rupees + random.randint(100, 500))
            ground_truth = 'escalate'

        elif arch_num == 3:
            # Expired/revoked mandate
            if random.random() < 0.5:
                mandate_status = 'revoked'
            else:
                mandate_valid_until = _ts(day_offset - 5)
                mandate_status = 'expired'
            ground_truth = 'escalate'

        elif arch_num == 4:
            # Wrong merchant
            wrong_merchants = [m for m in MERCHANTS if m != merchant]
            order_merchant = random.choice(wrong_merchants)
            ground_truth = 'escalate'

        elif arch_num == 5:
            # Not fulfilled
            order_status = 'placed'
            fulfilled_at = None
            reason_code = 'goods_or_services_not_received_or_partially_received'
            ground_truth = 'accept'

        elif arch_num == 6:
            # Timestamp inconsistency: fulfilled_at before placed_at
            fulfilled_at = placed_at - random.randint(3600, 7200)
            ground_truth = 'escalate'

        elif arch_num == 7:
            # Duplicate transaction -- handled by generating a second near-identical action chain
            # The duplicate itself is just the record existing; the rule engine will need
            # to detect it in Phase 2. For now, ground truth is escalate.
            ground_truth = 'escalate'

        elif arch_num == 8:
            # Clean legitimate, mislabeled reason code
            # All checks pass, but reason code doesn't match reality
            reason_code = 'non_matching_account_number'
            ground_truth = 'contest'

        mandate = Mandate(
            id=mandate_id,
            user_id=user_id,
            agent_id='claude_agent',
            merchant_id=merchant,
            spending_cap_amount=_paise(cap_rupees),
            spending_cap_currency='INR',
            valid_from=mandate_valid_from,
            valid_until=mandate_valid_until,
            status=mandate_status,
            created_at=mandate_valid_from,
        )

        actions = _make_action_chain(mandate_id, order_merchant, order_amount, day_offset)
        pay_action = actions[-1]

        order = Order(
            id=_next_id('order'),
            mandate_id=mandate_id,
            confirming_action_id=pay_action.id,
            merchant_id=order_merchant,
            amount=order_amount,
            currency='INR',
            status=order_status,
            placed_at=placed_at,
            fulfilled_at=fulfilled_at,
        )

        dispute = Dispute(
            id=_next_id('disp'),
            order_id=order.id,
            payment_id=f"pay_{_counters['disp']:04d}",
            amount=order.amount,
            currency='INR',
            amount_deducted=0,
            reason_code=reason_code,
            phase=random.choice(['chargeback', 'fraud']),
            status='open',
            respond_by=_ts(day_offset + 14),
            raised_at=_ts(day_offset + 2),
            ground_truth_label=ground_truth,
            is_held_out=i in held_out_indices,
        )

        is_held_out = i in held_out_indices

        records.append((mandate, actions, order, dispute, is_held_out))

        # Archetype 7: add a near-duplicate action chain to simulate the duplicate transaction
        if arch_num == 7:
            dup_actions = _make_action_chain(
                mandate_id, order_merchant, order_amount, day_offset
            )
            # Shift timestamps slightly to make them "near-identical but not exact"
            for da in dup_actions:
                da.timestamp += random.randint(60, 300)
            records[-1] = (mandate, actions + dup_actions, order, dispute, is_held_out)

    return records


def main():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'mandate_trail.db')

    # Wipe and recreate
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = db.init_db(db_path)

    # 8 archetypes, ~7-8 records each, 20 total held-out (~2-3 per archetype)
    archetype_configs = [
        # (archetype_num, count, held_out_count)
        (1, 8, 3),
        (2, 8, 3),
        (3, 8, 3),
        (4, 7, 2),
        (5, 7, 2),
        (6, 7, 2),
        (7, 7, 2),
        (8, 8, 3),
    ]

    total = 0
    held_out_total = 0

    for arch_num, count, ho_count in archetype_configs:
        records = _build_archetype(arch_num, count, ho_count)
        for mandate, actions, order, dispute, is_held_out in records:
            db.insert_mandate(conn, mandate)
            for action in actions:
                db.insert_agent_action(conn, action)
            db.insert_order(conn, order)
            db.insert_dispute(conn, dispute)
            total += 1
            if is_held_out:
                held_out_total += 1

    conn.commit()
    conn.close()

    print(f"Generated {total} disputes ({held_out_total} held-out) in {db_path}")

    # Verification: reopen and print summary
    conn = db.get_connection(db_path)
    for table in ['mandates', 'agent_actions', 'orders', 'disputes']:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")

    # Distribution by ground_truth_label
    rows = conn.execute(
        "SELECT ground_truth_label, COUNT(*) FROM disputes GROUP BY ground_truth_label"
    ).fetchall()
    print(f"  ground_truth_label distribution: {dict(rows)}")
    conn.close()


if __name__ == '__main__':
    main()
