"""
module_4/supabase_writer.py
Writes Module 4 client memory extractions to Supabase.
Tables: module4_client_memories, module4_run_logs
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from supabase_client import get_conn, insert_row, is_configured, upsert_row
except ImportError:
    def is_configured(): return False


def write_client_memory(run_id: str, raw_voice_note: str,
                        memory_obj: dict[str, Any],
                        model_used: str = "") -> int | None:
    if not is_configured():
        return None
    conn = get_conn()
    conf = memory_obj.get("confidence_summary", {})
    new_id = insert_row(conn, "module4_client_memories", {
        "run_id":               run_id,
        "raw_voice_note":       raw_voice_note,
        "summary":              memory_obj.get("summary", ""),
        "life_event":           memory_obj.get("life_event", {}),
        "timeline":             memory_obj.get("timeline", {}),
        "aesthetic_preference": memory_obj.get("aesthetic_preference", {}),
        "size_height":          memory_obj.get("size_height", {}),
        "budget":               memory_obj.get("budget", {}),
        "mood":                 memory_obj.get("mood", {}),
        "trend_signals":        memory_obj.get("trend_signals", {}),
        "next_step_intent":     memory_obj.get("next_step_intent", {}),
        "model_used":           model_used,
        "confidence_summary":   conf,
        "missing_fields_count": memory_obj.get("missing_fields_count", 0),
    })
    conn.close()
    if new_id:
        print(f"  [DB] module4_client_memories ← run={run_id} (id={new_id})")
    return new_id


def write_run_log(run_id: str, model_used: str,
                  records_processed: int = 0) -> int | None:
    if not is_configured():
        return None
    conn = get_conn()
    new_id = insert_row(conn, "module4_run_logs", {
        "run_id":            run_id,
        "model_used":        model_used,
        "records_processed": records_processed,
    })
    conn.close()
    return new_id


def write_profile_visit(visit_payload: dict[str, Any]) -> int | None:
    """
    Write one Module 4 visit payload into the shared V2 table:
    module4_client_visits
    """
    if not is_configured():
        return None

    meta = visit_payload.get("meta") or {}
    profile = visit_payload.get("ai_profile_edited") or {}
    visit_id = visit_payload.get("visit_id") or visit_payload.get("saved_at")
    client_name = (
        meta.get("client_display_name")
        or (meta.get("new_customer") or {}).get("name")
        or "未命名客户"
    )

    row = {
        "visit_id": visit_id,
        "client_name": client_name,
        "customer_segment": meta.get("customer_segment"),
        "saved_at": visit_payload.get("saved_at"),
        "raw_transcript_ca": visit_payload.get("raw_transcript_ca") or "",
        "summary": profile.get("summary", ""),
        "target_recipients": profile.get("target_recipients"),
        "life_event": profile.get("life_event"),
        "timeline": profile.get("timeline"),
        "aesthetic_preference": profile.get("aesthetic_preference"),
        "size_height": profile.get("size_height"),
        "budget": profile.get("budget"),
        "mood": profile.get("mood"),
        "trend_signals": profile.get("trend_signals"),
        "next_step_intent": profile.get("next_step_intent"),
        "interested_items": profile.get("interested_items"),
        "client_constraints": profile.get("client_constraints"),
        "purchase_frequency": profile.get("purchase_frequency"),
        "visit_purpose": profile.get("visit_purpose"),
        "purchase_decision_status": profile.get("purchase_decision_status"),
        "positive_signals": profile.get("positive_signals"),
        "negative_reasons": profile.get("negative_reasons"),
        "client_timeline": profile.get("client_timeline"),
        "ca_action_item": profile.get("ca_action_item"),
        "l1_client_profile": profile.get("L1_Client_Profile"),
        "l2_constraints": profile.get("L2_Constraints"),
        "l3_visit_funnel": profile.get("L3_Visit_Funnel"),
        "l4_next_steps": profile.get("L4_Next_Steps"),
        "full_profile": profile,
        "source": "module4_streamlit",
    }

    conn = get_conn()
    try:
        return upsert_row(conn, "module4_client_visits", row, conflict_col="visit_id")
    finally:
        conn.close()
