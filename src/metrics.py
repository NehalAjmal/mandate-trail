import sqlite3
from typing import Dict, Any

def compute_metrics(conn: sqlite3.Connection) -> Dict[str, Any]:
    # Computes precision, recall, and false-positive cost (per BACKEND_SCHEMA.md §4)
    # ONLY against the 20 held-out records.
    query = """
    SELECT 
        d.id as dispute_id,
        d.ground_truth_label,
        dec.recommended_action
    FROM disputes d
    JOIN decisions dec ON d.id = dec.dispute_id
    WHERE d.is_held_out = 1
    """
    
    rows = conn.execute(query).fetchall()
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    
    raw_data = []
    
    for dispute_id, ground_truth, recommended in rows:
        matched = 'Yes' if recommended == ground_truth else 'No'
        raw_data.append({
            "dispute_id": dispute_id,
            "recommended_action": recommended,
            "ground_truth_label": ground_truth,
            "matched": matched
        })
        
        if recommended == 'contest' and ground_truth == 'contest':
            true_positives += 1
        elif recommended == 'contest' and ground_truth != 'contest':
            false_positives += 1
        elif recommended != 'contest' and ground_truth == 'contest':
            false_negatives += 1
        elif recommended != 'contest' and ground_truth != 'contest':
            true_negatives += 1
            
    system_contests = true_positives + false_positives
    actual_contests = true_positives + false_negatives
    
    precision = (true_positives / system_contests) if system_contests > 0 else 0.0
    recall = (true_positives / actual_contests) if actual_contests > 0 else 0.0
    
    return {
        "precision": precision,
        "recall": recall,
        "false_positive_count": false_positives,
        "total_held_out": len(rows),
        "true_positives": true_positives,
        "false_negatives": false_negatives,
        "true_negatives": true_negatives,
        "raw_data": raw_data
    }
