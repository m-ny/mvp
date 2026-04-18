"""
Seed local Module 4 profile_*.json files into Supabase.

Usage:
    python module_4/seed_profiles_to_supabase.py

Requires:
    - root .env contains SUPABASE_PASSWORD
    - module_4/supabase_schema.sql has been executed once
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from supabase_client import get_conn, is_configured, upsert_row  # noqa: E402

DB_DIR = REPO / "module_4" / "database_mock"


def _load_profiles() -> list[dict]:
    rows: list[dict] = []
    for fp in sorted(DB_DIR.glob("profile_*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        meta = data.get("meta") or {}
        profile = data.get("ai_profile_edited") or {}
        client_name = (
            (meta.get("client_display_name") or "").strip()
            or ((meta.get("new_customer") or {}).get("name") or "").strip()
            or "未命名客户"
        )
        visit_id = data.get("visit_id") or data.get("saved_at") or fp.stem

        rows.append(
            {
                "visit_id": visit_id,
                "client_name": client_name,
                "customer_segment": meta.get("customer_segment"),
                "saved_at": data.get("saved_at"),
                "raw_transcript_ca": data.get("raw_transcript_ca") or "",
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
                "source": "module4_local_profile_json",
            }
        )
    return rows


def main() -> None:
    if not is_configured():
        raise SystemExit("SUPABASE_PASSWORD not set in root .env")

    rows = _load_profiles()
    if not rows:
        raise SystemExit("No local profile_*.json files found in module_4/database_mock")

    conn = get_conn()
    try:
        inserted = 0
        for row in rows:
            if upsert_row(conn, "module4_client_visits", row, conflict_col="visit_id") is not None:
                inserted += 1
        print(f"Seeded {inserted}/{len(rows)} Module 4 visits into module4_client_visits")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
