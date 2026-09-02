import time
import uuid
import json
from src import db
from src.rules_engine import evaluate_confidence
from src.evidence_writer import draft_narrative, perform_grounding_check
from src.models import Decision, EvidencePacket

def process_dispute(conn, dispute_id: str):
    dispute = db.get_dispute_by_id(conn, dispute_id)
    if not dispute:
        raise ValueError(f"Dispute {dispute_id} not found")
        
    order = db.get_order_by_id(conn, dispute.order_id)
    mandate = db.get_mandate_by_id(conn, order.mandate_id)
    actions = db.get_actions_for_mandate(conn, mandate.id)
    confirming_action = next(a for a in actions if a.id == order.confirming_action_id)
    
    now = int(time.time())
    db.insert_audit_log(conn, dispute.id, "dispute_ingested", json.dumps({"dispute_id": dispute.id}), now)
    
    # 1. Rule Engine
    score, checks = evaluate_confidence(order, mandate, confirming_action)
    db.insert_audit_log(conn, dispute.id, "rule_check_run", json.dumps({"score": score, "checks": checks}), now)
    
    # 2. Branch
    if score == 1.0:
        # High confidence -> try to contest
        narrative = draft_narrative(mandate, actions, order, dispute)
        passed, reason = perform_grounding_check(narrative, mandate, actions, order, dispute)
        
        if passed:
            evidence_id = f"ev_{uuid.uuid4().hex[:8]}"
            db.insert_audit_log(conn, dispute.id, "narrative_generated", json.dumps({"passed": True}), now)
            
            packet = EvidencePacket(
                id=evidence_id,
                dispute_id=dispute.id,
                narrative_text=narrative,
                grounding_check_passed=True,
                mapped_evidence_fields=json.dumps(["explanation_letter", "access_activity_log", "proof_of_service"]),
                generated_at=now
            )
            db.insert_evidence_packet(conn, packet)
            
            recommended_action = "contest"
        else:
            db.insert_audit_log(conn, dispute.id, "grounding_check_failed", json.dumps({"reason": reason}), now)
            recommended_action = "escalate"
    else:
        # Low confidence -> escalate
        recommended_action = "escalate"
        
    # 3. Record Decision
    decision = Decision(
        id=f"dec_{uuid.uuid4().hex[:8]}",
        dispute_id=dispute.id,
        confidence_score=score,
        checks_passed=json.dumps(checks),
        recommended_action=recommended_action,
        decided_at=now,
        decided_by="system"
    )
    db.insert_decision(conn, decision)
    db.insert_audit_log(conn, dispute.id, "decision_recorded", json.dumps({"action": recommended_action}), now)
    
    conn.commit()
    return decision
