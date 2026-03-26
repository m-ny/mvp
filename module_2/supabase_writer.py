"""
supabase_writer.py — Module 2 Supabase persistence helpers.

Writes trend shortlists and run logs to module2_* tables.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from supabase_client import get_conn, is_configured, insert_row, insert_rows


def write_shortlist(run_id: str, shortlist_output: dict) -> None:
    """Insert each shortlisted trend into module2_trend_shortlist."""
    if not is_configured():
        return
    conn = get_conn()
    try:
        rows = []
        for item in shortlist_output.get("shortlist", []):
            rows.append({
                "run_id": run_id,
                "module1_run_id": shortlist_output.get("module1_run_id"),
                "brand": shortlist_output.get("brand"),
                "trend_id": item.get("trend_id"),
                "rank": item.get("rank"),
                "label": item.get("label"),
                "category": item.get("category"),
                "composite_score": item.get("composite_score"),
                "score_freshness": (item.get("scores") or {}).get("freshness"),
                "score_brand_fit": (item.get("scores") or {}).get("brand_fit"),
                "score_category_fit": (item.get("scores") or {}).get("category_fit"),
                "score_materiality": (item.get("scores") or {}).get("materiality"),
                "score_actionability": (item.get("scores") or {}).get("actionability"),
                "confidence": item.get("confidence"),
                "why_selected": item.get("why_selected"),
                "evidence_references": item.get("evidence_references", []),
                "metric_signal": item.get("metric_signal", {}),
            })
        if rows:
            insert_rows(conn, "module2_trend_shortlist", rows)
            print(f"[Supabase] Inserted {len(rows)} shortlist rows.")
    finally:
        conn.close()


def write_run_log(
    run_id: str,
    module1_run_id: str,
    total_input: int,
    prefilter_rejected: int,
    passed_to_llm: int,
    shortlisted: int,
    generated_at: str,
) -> None:
    """Insert a run log row into module2_run_logs."""
    if not is_configured():
        return
    conn = get_conn()
    try:
        insert_row(conn, "module2_run_logs", {
            "run_id": run_id,
            "module1_run_id": module1_run_id,
            "total_input": total_input,
            "prefilter_rejected": prefilter_rejected,
            "passed_to_llm": passed_to_llm,
            "shortlisted": shortlisted,
            "noise_reduction_pct": round((total_input - shortlisted) / max(total_input, 1) * 100, 1),
            "generated_at": generated_at,
        })
        print("[Supabase] Run log inserted.")
    finally:
        conn.close()
