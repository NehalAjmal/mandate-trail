# pyrefly: ignore [missing-import, missing-module]
import pytest
import sqlite3
from src.metrics import compute_metrics

def test_compute_metrics():
    conn = sqlite3.connect(':memory:')
    conn.execute("CREATE TABLE disputes (id TEXT PRIMARY KEY, ground_truth_label TEXT, is_held_out BOOLEAN)")
    conn.execute("CREATE TABLE decisions (id TEXT PRIMARY KEY, dispute_id TEXT, recommended_action TEXT)")
    
    # 2 True Positives
    conn.execute("INSERT INTO disputes VALUES ('d1', 'contest', 1)")
    conn.execute("INSERT INTO decisions VALUES ('dec1', 'd1', 'contest')")
    conn.execute("INSERT INTO disputes VALUES ('d2', 'contest', 1)")
    conn.execute("INSERT INTO decisions VALUES ('dec2', 'd2', 'contest')")
    
    # 1 False Positive
    conn.execute("INSERT INTO disputes VALUES ('d3', 'escalate', 1)")
    conn.execute("INSERT INTO decisions VALUES ('dec3', 'd3', 'contest')")
    
    # 1 False Negative
    conn.execute("INSERT INTO disputes VALUES ('d4', 'contest', 1)")
    conn.execute("INSERT INTO decisions VALUES ('dec4', 'd4', 'escalate')")
    
    # 1 True Negative
    conn.execute("INSERT INTO disputes VALUES ('d5', 'accept', 1)")
    conn.execute("INSERT INTO decisions VALUES ('dec5', 'd5', 'escalate')")
    
    # 1 Not held out (should be ignored entirely)
    conn.execute("INSERT INTO disputes VALUES ('d6', 'escalate', 0)")
    conn.execute("INSERT INTO decisions VALUES ('dec6', 'd6', 'contest')")
    
    conn.commit()
    
    metrics = compute_metrics(conn)
    
    assert metrics["total_held_out"] == 5
    assert metrics["false_positive_count"] == 1
    assert abs(metrics["precision"] - 0.666) < 0.01
    assert abs(metrics["recall"] - 0.666) < 0.01
