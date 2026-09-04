-- Schema for mandate_trail.db, matching BACKEND_SCHEMA.md §1 exactly.
-- Created fresh by data/seed/generate_dataset.py on each run.

CREATE TABLE mandates (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    merchant_id TEXT NOT NULL,
    spending_cap_amount INTEGER NOT NULL,
    spending_cap_currency TEXT NOT NULL DEFAULT 'INR',
    valid_from INTEGER NOT NULL,
    valid_until INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
    created_at INTEGER NOT NULL
);

CREATE TABLE agent_actions (
    id TEXT PRIMARY KEY,
    mandate_id TEXT NOT NULL REFERENCES mandates(id),
    action_type TEXT NOT NULL CHECK (action_type IN ('search', 'select', 'confirm', 'pay')),
    merchant_id TEXT NOT NULL,
    item_description TEXT NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    timestamp INTEGER NOT NULL,
    raw_payload TEXT NOT NULL
);

CREATE TABLE orders (
    id TEXT PRIMARY KEY,
    mandate_id TEXT NOT NULL REFERENCES mandates(id),
    confirming_action_id TEXT NOT NULL REFERENCES agent_actions(id),
    merchant_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL CHECK (status IN ('placed', 'fulfilled', 'cancelled')),
    placed_at INTEGER NOT NULL,
    fulfilled_at INTEGER
);

CREATE TABLE disputes (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(id),
    payment_id TEXT NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    amount_deducted INTEGER NOT NULL DEFAULT 0,
    reason_code TEXT NOT NULL,
    phase TEXT NOT NULL CHECK (phase IN ('chargeback', 'fraud')),
    status TEXT NOT NULL CHECK (status IN ('open', 'under_review', 'action_required', 'won', 'lost', 'closed')),
    respond_by INTEGER NOT NULL,
    raised_at INTEGER NOT NULL,
    ground_truth_label TEXT NOT NULL CHECK (ground_truth_label IN ('contest', 'escalate', 'accept')),
    is_held_out BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE evidence_packets (
    id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL UNIQUE REFERENCES disputes(id),
    narrative_text TEXT NOT NULL,
    grounding_check_passed BOOLEAN NOT NULL,
    mapped_evidence_fields TEXT NOT NULL,
    generated_at INTEGER NOT NULL
);

CREATE TABLE decisions (
    id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL UNIQUE REFERENCES disputes(id),
    confidence_score REAL NOT NULL,
    checks_passed TEXT NOT NULL,
    recommended_action TEXT NOT NULL CHECK (recommended_action IN ('contest', 'escalate', 'accept')),
    decided_at INTEGER NOT NULL,
    decided_by TEXT NOT NULL CHECK (decided_by IN ('system', 'human'))
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dispute_id TEXT NOT NULL REFERENCES disputes(id),
    event_type TEXT NOT NULL,
    event_payload TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
