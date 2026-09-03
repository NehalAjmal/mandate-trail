# pyrefly: ignore [missing-import,missing-module]
import streamlit as st
import sqlite3
import pandas as pd
import json
import time
import os

from src.metrics import compute_metrics
from src import db

DB_PATH = "data/mandate_trail.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

st.set_page_config(page_title="Mandate Trail", layout="wide")
st.title("Mandate Trail")

if "selected_dispute_id" not in st.session_state:
    st.session_state.selected_dispute_id = None

tab_queue, tab_metrics = st.tabs(["Queue", "Metrics"])

def format_inr(paise):
    return f"₹{paise/100:,.2f}"

def format_ts(ts):
    from datetime import datetime, timezone
    if not ts: return "None"
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def render_queue():
    conn = get_conn()
    
    query = """
    SELECT 
        d.id as dispute_id,
        d.reason_code,
        d.amount,
        dec.confidence_score,
        dec.recommended_action,
        d.status as razorpay_status
    FROM disputes d
    LEFT JOIN decisions dec ON d.id = dec.dispute_id
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        st.info("No disputes found. Please run the backend first.")
        return
        
    df['amount_formatted'] = df['amount'].apply(format_inr)
    
    filter_val = st.selectbox("Filter by recommended action", ["All", "contest", "escalate", "accept"])
    if filter_val != "All":
        df = df[df['recommended_action'] == filter_val]
        
    df = df.sort_values(by='confidence_score', ascending=True)
    
    st.dataframe(df[['dispute_id', 'reason_code', 'amount_formatted', 'confidence_score', 'recommended_action', 'razorpay_status']], hide_index=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        selected_id = st.selectbox("Select a Dispute to view details:", [""] + list(df['dispute_id'].values))
    with col2:
        st.write("") # spacer
        st.write("") # spacer
        if st.button("View Detail"):
            if selected_id:
                st.session_state.selected_dispute_id = selected_id
                st.rerun()

def get_action_prefix(action):
    if action == 'contest': return '🟢 Contest'
    if action == 'escalate': return '🟡 Escalate'
    if action in ['closed', 'accept', 'accepted']: return '⚪ Closed'
    return action

def get_grounding_prefix(passed):
    return '✓ Grounded' if passed else '✗ Rejected — escalated instead'

def render_detail(dispute_id):
    if st.button("← Back to queue"):
        st.session_state.selected_dispute_id = None
        st.rerun()
        
    conn = get_conn()
    dispute = db.get_dispute_by_id(conn, dispute_id)
    order = db.get_order_by_id(conn, dispute.order_id)
    mandate = db.get_mandate_by_id(conn, order.mandate_id)
    actions = db.get_actions_for_mandate(conn, mandate.id)
    
    decision = db.get_decision_for_dispute(conn, dispute_id)
    evidence_row = conn.execute("SELECT * FROM evidence_packets WHERE dispute_id=?", (dispute_id,)).fetchone()
    audits = conn.execute("SELECT * FROM audit_log WHERE dispute_id=? ORDER BY created_at ASC", (dispute_id,)).fetchall()
    
    if not decision:
        st.warning("No decision found.")
        conn.close()
        return
        
    recommended_action = decision.recommended_action
    confidence_score = decision.confidence_score
    checks_passed = json.loads(decision.checks_passed)
    decided_by = decision.decided_by
    
    st.header(f"{dispute.id} - {dispute.reason_code}")
    st.subheader(f"Amount: {format_inr(dispute.amount)} | Razorpay: {dispute.status} | Recommendation: {get_action_prefix(recommended_action)}")
    
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Mandate**")
        st.write(f"Cap: {format_inr(mandate.spending_cap_amount)}")
        st.write(f"Valid: {format_ts(mandate.valid_from)} to {format_ts(mandate.valid_until)}")
        st.write(f"Merchant: {mandate.merchant_id}")
        
    with col2:
        st.markdown("**Agent Action Log**")
        for a in actions:
            st.write(f"- {format_ts(a.timestamp)}: {a.action_type} - {format_inr(a.amount)}")
            
    with col3:
        st.markdown("**Fulfillment**")
        st.write(f"Status: {order.status}")
        st.write(f"Fulfilled At: {format_ts(order.fulfilled_at)}")
        
    st.divider()
    
    st.markdown("**Rule Engine Result**")
    st.write(f"Confidence Score: {confidence_score:.2f}")
    for check, passed in checks_passed.items():
        st.write(f"- {check}: {'Pass' if passed else 'Fail'}")
        
    st.divider()
    
    st.markdown("**Evidence Narrative**")
    if evidence_row:
        grounding_passed = evidence_row[3]
        st.markdown(f"**{get_grounding_prefix(grounding_passed)}**")
        st.write(evidence_row[2])
    else:
        st.info("No evidence narrative generated for this dispute (escalated case).")
        
    st.divider()
    
    # Action Buttons
    if recommended_action == 'contest' and decided_by == 'system':
        if st.button("Approve & mark contested"):
            conn.execute("UPDATE decisions SET decided_by = 'human' WHERE dispute_id=?", (dispute_id,))
            db.insert_audit_log(conn, dispute_id, "human_approval", "{}", int(time.time()))
            conn.commit()
            st.rerun()
    elif recommended_action == 'contest' and decided_by == 'human':
        st.write("✓ Approved by reviewer")
        
    if recommended_action == 'escalate':
        if st.button("Mark as manually resolved"):
            conn.execute("UPDATE decisions SET decided_by = 'human' WHERE dispute_id=?", (dispute_id,))
            db.insert_audit_log(conn, dispute_id, "human_override", "{}", int(time.time()))
            conn.commit()
            st.rerun()
            
    if recommended_action == 'contest':
        if st.button("Escalate to human"):
            conn.execute("UPDATE decisions SET recommended_action = 'escalate', decided_by = 'human' WHERE dispute_id=?", (dispute_id,))
            db.insert_audit_log(conn, dispute_id, "human_override", "{}", int(time.time()))
            conn.commit()
            st.rerun()
            
    with st.expander("Raw Audit Log"):
        logs = [{"event_type": row[2], "payload": json.loads(row[3]), "time": format_ts(row[4])} for row in audits]
        st.json(logs)
        
    conn.close()

def render_metrics():
    conn = get_conn()
    metrics = compute_metrics(conn)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Precision", f"{metrics['precision']:.2f}")
    col2.metric("Recall", f"{metrics['recall']:.2f}")
    col3.metric("False-positive count", f"{metrics['false_positive_count']}")
    
    st.markdown("*(False positives represent cases with card-network penalty risk and wasted ops time on a case that shouldn't have been fought)*")
    
    st.markdown("### Held-Out Records (20)")
    query = """
    SELECT 
        d.id as dispute_id,
        dec.recommended_action,
        d.ground_truth_label,
        CASE WHEN dec.recommended_action = d.ground_truth_label THEN 'Yes' ELSE 'No' END as matched
    FROM disputes d
    JOIN decisions dec ON d.id = dec.dispute_id
    WHERE d.is_held_out = 1
    """
    df = pd.read_sql_query(query, conn)
    st.dataframe(df, hide_index=True)
    
    conn.close()
    
    st.markdown("### What broke")
    try:
        with open("hallucination_failure_story.md", "r") as f:
            st.markdown(f.read())
    except FileNotFoundError:
        st.write("Failure story not found.")

with tab_queue:
    if st.session_state.selected_dispute_id:
        render_detail(st.session_state.selected_dispute_id)
    else:
        render_queue()

with tab_metrics:
    render_metrics()
