import os
import sqlite3
from src import db
from src.decision import process_dispute
from src.evidence_writer import perform_grounding_check, draft_narrative


def test_grounding_unit_check():
    """Unit test: a hand-crafted bad narrative gets caught by the deterministic grounding check."""
    print("\n=== Grounding Check Unit Test (hardcoded bad narrative) ===")
    conn = db.get_connection()
    disputes = db.get_all_disputes(conn)
    target = None

    for d in disputes:
        o = db.get_order_by_id(conn, d.order_id)
        m = db.get_mandate_by_id(conn, o.mandate_id)
        actions = db.get_actions_for_mandate(conn, m.id)
        if len(actions) > 4:
            target = (d, o, m, actions)
            break

    if not target:
        print("Could not find a multi-action record for the unit test.")
        conn.close()
        return

    dispute, order, mandate, actions = target
    bad_narrative = (
        "The order was placed legitimately on the merchant platform. "
        "We have verified that the user logged in from IP address 123.45.67.89 "
        "using their registered Safari browser and clicked the checkout button. "
        "The device fingerprint matches their previous history."
    )
    print(f"Testing against dispute {dispute.id}")
    passed, reason = perform_grounding_check(bad_narrative, mandate, actions, order, dispute)
    print(f"Grounding Check Passed: {passed}")
    print(f"Reason: {reason}")
    assert not passed, "Grounding check should have rejected the fabricated narrative"
    conn.close()


def run_all():
    print("\n=== End-to-End Decision Run on All 60 Records ===")
    conn = db.get_connection()
    disputes = db.get_all_disputes(conn)

    success_count = 0
    crash_count = 0

    for d in disputes:
        try:
            decision = process_dispute(conn, d.id)
            success_count += 1
        except Exception as e:
            print(f"Crash on {d.id}: {str(e)}")
            crash_count += 1

    print(f"Processed {success_count} records with {crash_count} crashes.")

    decisions = conn.execute("SELECT recommended_action, COUNT(*) FROM decisions GROUP BY recommended_action").fetchall()
    print("Decisions made:", decisions)
    conn.close()


if __name__ == '__main__':
    test_grounding_unit_check()
    run_all()
