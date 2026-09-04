import os
import sqlite3
from src.models import Mandate, AgentAction, Order, Dispute, EvidencePacket, Decision, AuditLogEntry

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'mandate_trail.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'schema.sql')


def get_connection(db_path=None):
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    conn = get_connection(db_path)
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    return conn


# --- Inserts ---

def insert_mandate(conn, m: Mandate):
    conn.execute(
        "INSERT INTO mandates VALUES (?,?,?,?,?,?,?,?,?,?)",
        (m.id, m.user_id, m.agent_id, m.merchant_id, m.spending_cap_amount,
         m.spending_cap_currency, m.valid_from, m.valid_until, m.status, m.created_at)
    )


def insert_agent_action(conn, a: AgentAction):
    conn.execute(
        "INSERT INTO agent_actions VALUES (?,?,?,?,?,?,?,?,?)",
        (a.id, a.mandate_id, a.action_type, a.merchant_id, a.item_description,
         a.amount, a.currency, a.timestamp, a.raw_payload)
    )


def insert_order(conn, o: Order):
    conn.execute(
        "INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)",
        (o.id, o.mandate_id, o.confirming_action_id, o.merchant_id, o.amount,
         o.currency, o.status, o.placed_at, o.fulfilled_at)
    )


def insert_dispute(conn, d: Dispute):
    conn.execute(
        "INSERT INTO disputes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (d.id, d.order_id, d.payment_id, d.amount, d.currency, d.amount_deducted,
         d.reason_code, d.phase, d.status, d.respond_by, d.raised_at,
         d.ground_truth_label, d.is_held_out)
    )


def insert_evidence_packet(conn, e: EvidencePacket):
    conn.execute(
        "INSERT INTO evidence_packets VALUES (?,?,?,?,?,?)",
        (e.id, e.dispute_id, e.narrative_text, e.grounding_check_passed,
         e.mapped_evidence_fields, e.generated_at)
    )


def insert_decision(conn, d: Decision):
    conn.execute(
        "INSERT INTO decisions VALUES (?,?,?,?,?,?,?)",
        (d.id, d.dispute_id, d.confidence_score, d.checks_passed,
         d.recommended_action, d.decided_at, d.decided_by)
    )


def insert_audit_log(conn, dispute_id: str, event_type: str, event_payload: str, created_at: int):
    conn.execute(
        "INSERT INTO audit_log (dispute_id, event_type, event_payload, created_at) VALUES (?,?,?,?)",
        (dispute_id, event_type, event_payload, created_at)
    )


# --- Reads ---

def _row_to_mandate(row):
    return Mandate(*row)

def _row_to_action(row):
    return AgentAction(*row)

def _row_to_order(row):
    return Order(*row)

def _row_to_dispute(row):
    return Dispute(*row)

def _row_to_decision(row):
    return Decision(*row)


def get_all_disputes(conn):
    rows = conn.execute("SELECT * FROM disputes").fetchall()
    return [_row_to_dispute(r) for r in rows]


def get_dispute_by_id(conn, dispute_id: str):
    row = conn.execute("SELECT * FROM disputes WHERE id = ?", (dispute_id,)).fetchone()
    return _row_to_dispute(row) if row else None


def get_mandate_by_id(conn, mandate_id: str):
    row = conn.execute("SELECT * FROM mandates WHERE id = ?", (mandate_id,)).fetchone()
    return _row_to_mandate(row) if row else None


def get_order_by_id(conn, order_id: str):
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    return _row_to_order(row) if row else None


def get_actions_for_mandate(conn, mandate_id: str):
    rows = conn.execute(
        "SELECT * FROM agent_actions WHERE mandate_id = ? ORDER BY timestamp", (mandate_id,)
    ).fetchall()
    return [_row_to_action(r) for r in rows]


def get_orders_for_mandate(conn, mandate_id: str):
    rows = conn.execute(
        "SELECT * FROM orders WHERE mandate_id = ? ORDER BY placed_at", (mandate_id,)
    ).fetchall()
    return [_row_to_order(r) for r in rows]


def get_decision_for_dispute(conn, dispute_id: str):
    row = conn.execute(
        "SELECT * FROM decisions WHERE dispute_id = ?", (dispute_id,)
    ).fetchone()
    return _row_to_decision(row) if row else None


def get_evidence_packet_for_dispute(conn, dispute_id: str):
    row = conn.execute(
        "SELECT * FROM evidence_packets WHERE dispute_id = ?", (dispute_id,)
    ).fetchone()
    return EvidencePacket(*row) if row else None


def get_audit_log_for_dispute(conn, dispute_id: str):
    rows = conn.execute(
        "SELECT * FROM audit_log WHERE dispute_id = ? ORDER BY created_at", (dispute_id,)
    ).fetchall()
    return [AuditLogEntry(*r) for r in rows]
