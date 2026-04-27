"""
module_5/supabase_reader.py
Read Module 5 inputs from Supabase — the same tables Module 2 and Module 4 write to.

  - module2_trend_shortlist   ← Module 2 shortlist output (full extended schema)
  - module4_client_memories   ← Module 4 structured memory output

Optional env (pin a specific pipeline run):
  M5_MODULE2_RUN_ID  — module2_trend_shortlist.run_id (default: latest by created_at)
  M5_MODULE4_RUN_ID  — module4_client_memories.run_id (default: latest by generated_at)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase_client import get_conn, is_configured


_CACHE_DIR = Path(__file__).resolve().parent / "_cache"
_M2_CACHE_VERSION = "m2_fast_extras_v1"


def _m2_cache_path(run_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in run_id)
    return _CACHE_DIR / f"module2_trend_shortlist_{safe}.json"


def _cache_enabled() -> bool:
    return os.environ.get("M5_DISABLE_M2_CACHE", "").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    )


def _jsonb(val: Any) -> Any:
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return val


def _confidence_obj(val: Any) -> Any:
    """Normalize M4 visit profile objects from {_value,_evidence,_confidence} to legacy shape."""
    val = _jsonb(val)
    if isinstance(val, dict) and any(k in val for k in ("_value", "_evidence", "_confidence")):
        return {
            "value": val.get("_value"),
            "confidence": val.get("_confidence"),
            "evidence": val.get("_evidence"),
        }
    return val if val is not None else {}


def _ts(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


_M2_SELECT = """
SELECT trend_id, rank, label, category, composite_score,
       score_freshness, score_brand_fit, score_category_fit,
       score_materiality, score_actionability,
       score_ca_conversational_utility, score_language_specificity,
       score_client_persona_match, score_novelty, score_trend_velocity,
       score_cross_run_persistence,
       confidence, why_selected, evidence_references, metric_signal,
       brand, module1_run_id,
       location, data_type, subcategory, client_persona_match_name, hero_product,
       hero_product_source,
       engagement_recency_pct, low_signal_warning, no_date_signal, disqualifying_reason
FROM module2_trend_shortlist
WHERE run_id = %s ORDER BY rank NULLS LAST, trend_id
"""


_M2_SELECT_GROUPS: tuple[tuple[str, ...], ...] = (
    (
        "trend_id",
        "rank",
        "label",
        "category",
        "composite_score",
        "confidence",
        "brand",
        "module1_run_id",
    ),
    (
        "trend_id",
        "score_freshness",
        "score_brand_fit",
        "score_category_fit",
        "score_materiality",
        "score_actionability",
        "score_ca_conversational_utility",
        "score_language_specificity",
        "score_client_persona_match",
        "score_novelty",
        "score_trend_velocity",
        "score_cross_run_persistence",
    ),
    ("trend_id", "why_selected"),
    ("trend_id", "evidence_references"),
    ("trend_id", "metric_signal"),
    (
        "trend_id",
        "location",
        "data_type",
        "subcategory",
        "client_persona_match_name",
        "hero_product",
        "hero_product_source",
        "engagement_recency_pct",
        "low_signal_warning",
        "no_date_signal",
        "disqualifying_reason",
    ),
)


def _fetch_m2_rows(run_id: str) -> list[dict[str, Any]]:
    """
    Fetch M2 shortlist rows in narrow column groups.

    Some Supabase pooler connections in the class project hang on one wide SELECT
    across all M2 columns, while the same columns read quickly in small groups.
    Keep this split local to the reader so downstream M5 still receives the same
    row shape.
    """
    fast_mode = os.environ.get("M5_M2_FAST_MODE", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )
    if fast_mode:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SET statement_timeout = '15000ms'")
            cur.execute(
                "SELECT trend_id, rank, label, category, composite_score, confidence, "
                "       brand, module1_run_id "
                "FROM module2_trend_shortlist WHERE run_id = %s",
                (run_id,),
            )
            names = [d[0] for d in cur.description]
            rows = [dict(zip(names, raw)) for raw in cur.fetchall()]
            by_tid = {str(r.get("trend_id")): r for r in rows if r.get("trend_id") is not None}
            extra_cols = (
                "why_selected",
                "evidence_references",
                "metric_signal",
                "location",
                "data_type",
                "subcategory",
                "client_persona_match_name",
                "hero_product",
                "hero_product_source",
                "engagement_recency_pct",
                "low_signal_warning",
                "no_date_signal",
                "disqualifying_reason",
            )
            # Fetch text/json extras one column at a time. In this Supabase pooler,
            # mixing these with the core columns can hang even for 15 rows.
            for col in extra_cols:
                extra_conn = get_conn()
                try:
                    extra_cur = extra_conn.cursor()
                    extra_cur.execute("SET statement_timeout = '15000ms'")
                    extra_cur.execute(
                        f"SELECT trend_id, {col} FROM module2_trend_shortlist "
                        "WHERE run_id = %s ORDER BY rank NULLS LAST, trend_id",
                        (run_id,),
                    )
                    for tid, val in extra_cur.fetchall():
                        if str(tid) in by_tid:
                            by_tid[str(tid)][col] = val
                finally:
                    extra_conn.close()
            return sorted(
                rows,
                key=lambda r: (
                    int(r["rank"]) if r.get("rank") is not None else 10**9,
                    str(r.get("trend_id") or ""),
                ),
            )
        finally:
            conn.close()

    by_tid: dict[str, dict[str, Any]] = {}
    for cols in _M2_SELECT_GROUPS:
        select_cols = ", ".join(cols)
        # Use a short fresh connection per column group. In the shared Supabase
        # pooler used by this project, repeated wide/narrow reads on one session
        # can hang while the same small query succeeds immediately on a fresh
        # connection.
        last_error: Exception | None = None
        for _attempt in range(2):
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("SET statement_timeout = '15000ms'")
                cur.execute(
                    f"SELECT {select_cols} FROM module2_trend_shortlist WHERE run_id = %s",
                    (run_id,),
                )
                names = [d[0] for d in cur.description]
                for raw in cur.fetchall():
                    row = dict(zip(names, raw))
                    tid = row["trend_id"]
                    by_tid.setdefault(tid, {}).update(row)
                last_error = None
                break
            except Exception as e:
                last_error = e
            finally:
                conn.close()
        if last_error is not None:
            raise last_error

    def sort_key(r: dict[str, Any]) -> tuple[int, str]:
        rank = r.get("rank")
        try:
            rank_i = int(rank)
        except (TypeError, ValueError):
            rank_i = 10**9
        return rank_i, str(r.get("trend_id") or "")

    return sorted(by_tid.values(), key=sort_key)


def read_trend_shortlist(run_id: str | None = None) -> dict[str, Any]:
    """
    Read rows from module2_trend_shortlist (written by Module 2).
    If run_id is None, uses M5_MODULE2_RUN_ID or the most recent run in the table.
    Returns: {"query_context": {...}, "trends": [...]} for M5.
    """
    run_id = (run_id or os.environ.get("M5_MODULE2_RUN_ID", "").strip()) or None

    if run_id and _cache_enabled():
        cache_path = _m2_cache_path(run_id)
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if (cached.get("query_context") or {}).get("m5_m2_cache_version") == _M2_CACHE_VERSION:
                    return cached
            except (OSError, json.JSONDecodeError):
                pass

    if run_id is None:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT run_id FROM module2_trend_shortlist "
            "ORDER BY created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            raise ValueError("No trend shortlist rows found in module2_trend_shortlist.")
        run_id = row[0]
        conn.close()

    rows = _fetch_m2_rows(run_id)

    if not rows:
        raise ValueError(f"No trends found for run_id={run_id} in module2_trend_shortlist.")

    meta = rows[0]
    query_context = {
        "brand": meta.get("brand"),
        "module1_run_id": meta.get("module1_run_id"),
        "module2_run_id": run_id,
        "source": "supabase:module2_trend_shortlist",
        "m5_m2_cache_version": _M2_CACHE_VERSION,
    }

    trends = []
    for r in rows:
        trends.append({
            "trend_id": r["trend_id"],
            "trend_label": r["label"],
            "category": r["category"] or "",
            "cluster_summary": r.get("why_selected") or "",
            "composite_score": _float(r.get("composite_score")),
            "scores": {
                "freshness": _float(r.get("score_freshness")),
                "brand_fit": _float(r.get("score_brand_fit")),
                "category_fit": _float(r.get("score_category_fit")),
                "materiality": _float(r.get("score_materiality")),
                "actionability": _float(r.get("score_actionability")),
                "ca_conversational_utility": _float(r.get("score_ca_conversational_utility")),
                "language_specificity": _float(r.get("score_language_specificity")),
                "client_persona_match": _float(r.get("score_client_persona_match")),
                "novelty": _float(r.get("score_novelty")),
                "trend_velocity": _float(r.get("score_trend_velocity")),
                "cross_run_persistence": _float(r.get("score_cross_run_persistence")),
            },
            "confidence": r.get("confidence"),
            "evidence_references": _jsonb(r.get("evidence_references", [])),
            "metric_signal": _jsonb(r.get("metric_signal", {})),
            "rank": r.get("rank"),
            "source_format": "module2_trend_shortlist",
            "location": r.get("location"),
            "data_type": r.get("data_type"),
            "subcategory": r.get("subcategory"),
            "client_persona_match_name": r.get("client_persona_match_name"),
            "hero_product": r.get("hero_product"),
            "hero_product_source": r.get("hero_product_source"),
            "engagement_recency_pct": _float(r.get("engagement_recency_pct")),
            "low_signal_warning": r.get("low_signal_warning"),
            "no_date_signal": r.get("no_date_signal"),
            "disqualifying_reason": r.get("disqualifying_reason"),
        })

    out = {"query_context": query_context, "trends": trends}
    if _cache_enabled():
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _m2_cache_path(run_id).write_text(
                json.dumps(out, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
    return out


def _row_to_m5_client(r: dict[str, Any]) -> dict[str, Any]:
    """
    Map a module4_client_memories row to one M5 'client' object.
    Uses client_id / display_name / persona_tag / vip_tier when present (PRD columns).
    """
    rid = r.get("run_id", "unknown")
    db_id = r.get("id")
    cid = (r.get("client_id") or "").strip()
    if not cid:
        cid = f"m4_{rid}_{db_id}"
    display = (r.get("display_name") or "").strip()
    if not display:
        display = "Client (Module 4)"
    ptag = (r.get("persona_tag") or "").strip()
    if not ptag:
        ptag = "module4_structured_memory"
    vip = (r.get("vip_tier") or "").strip()
    if not vip:
        vip = "N/A"

    return {
        "memory_row_id": db_id,
        "client_id": cid,
        "name": display,
        "persona_tag": ptag,
        "vip_tier": vip,
        "source_table": "module4_client_memories",
        "module4_run_id": rid,
        "module4_memory_row_id": db_id,
        "generated_at": _ts(r.get("generated_at")),
        "model_used": r.get("model_used"),
        "missing_fields_count": r.get("missing_fields_count"),
        "raw_voice_note": r.get("raw_voice_note") or "",
        "summary": r.get("summary") or "",
        "life_event": _jsonb(r.get("life_event", {})),
        "timeline": _jsonb(r.get("timeline", {})),
        "aesthetic_preference": _jsonb(r.get("aesthetic_preference", {})),
        "size_height": _jsonb(r.get("size_height", {})),
        "budget": _jsonb(r.get("budget", {})),
        "mood": _jsonb(r.get("mood", {})),
        "trend_signals": _jsonb(r.get("trend_signals", {})),
        "next_step_intent": _jsonb(r.get("next_step_intent", {})),
        "confidence_summary": _jsonb(r.get("confidence_summary", {})),
    }


def _profile_pick(profile: dict[str, Any], key: str) -> Any:
    if not isinstance(profile, dict):
        return None
    return profile.get(key)


def _row_to_m5_visit_client(r: dict[str, Any]) -> dict[str, Any]:
    """
    Map new Module 4 visit rows to the M5 client-memory object.

    New M4 writes to module4_client_visits. Most structured fields currently live
    in full_profile using {_value,_evidence,_confidence}; expose both a normalized
    legacy-compatible shape and the richer visit/funnel fields.
    """
    profile = _jsonb(r.get("full_profile")) or {}
    db_id = r.get("id")
    visit_id = (r.get("visit_id") or "").strip()
    name = (r.get("client_name") or "").strip() or "Client (Module 4 Visit)"
    cid = visit_id or f"m4_visit_{db_id}"
    segment = (r.get("customer_segment") or "").strip() or "module4_client_visit"

    def field(key: str) -> Any:
        return _confidence_obj(r.get(key) if r.get(key) is not None else _profile_pick(profile, key))

    # full_profile uses capitalized layer keys in the current M4 export.
    l1 = _jsonb(r.get("l1_client_profile")) or _profile_pick(profile, "L1_Client_Profile") or {}
    l2 = _jsonb(r.get("l2_constraints")) or _profile_pick(profile, "L2_Constraints") or {}
    l3 = _jsonb(r.get("l3_visit_funnel")) or _profile_pick(profile, "L3_Visit_Funnel") or {}
    l4 = _jsonb(r.get("l4_next_steps")) or _profile_pick(profile, "L4_Next_Steps") or {}

    return {
        "memory_row_id": db_id,
        "client_id": cid,
        "name": name,
        "persona_tag": segment,
        "vip_tier": "N/A",
        "source_table": "module4_client_visits",
        "module4_visit_id": visit_id,
        "module4_visit_row_id": db_id,
        "module4_source": r.get("source"),
        "saved_at": _ts(r.get("saved_at")),
        "created_at": _ts(r.get("created_at")),
        "updated_at": _ts(r.get("updated_at")),
        "raw_voice_note": r.get("raw_transcript_ca") or "",
        "raw_transcript_ca": r.get("raw_transcript_ca") or "",
        "summary": r.get("summary") or profile.get("summary") or "",
        "life_event": field("life_event"),
        "timeline": field("timeline"),
        "aesthetic_preference": field("aesthetic_preference"),
        "size_height": field("size_height"),
        "budget": field("budget"),
        "mood": field("mood"),
        "trend_signals": field("trend_signals"),
        "next_step_intent": field("next_step_intent"),
        "target_recipients": field("target_recipients"),
        "interested_items": field("interested_items"),
        "client_constraints": field("client_constraints"),
        "purchase_frequency": field("purchase_frequency"),
        "visit_purpose": field("visit_purpose"),
        "purchase_decision_status": field("purchase_decision_status"),
        "positive_signals": field("positive_signals"),
        "negative_reasons": field("negative_reasons"),
        "client_timeline": field("client_timeline"),
        "ca_action_item": field("ca_action_item"),
        "l1_client_profile": _jsonb(l1) or {},
        "l2_constraints": _jsonb(l2) or {},
        "l3_visit_funnel": _jsonb(l3) or {},
        "l4_next_steps": _jsonb(l4) or {},
        "full_profile": profile,
    }


def _resolve_m4_run_id(cur, run_id: str | None) -> str:
    run_id = (run_id or os.environ.get("M5_MODULE4_RUN_ID", "").strip()) or None
    if run_id is None:
        cur.execute(
            "SELECT run_id FROM module4_client_memories "
            "ORDER BY generated_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            raise ValueError("No rows found in module4_client_memories.")
        run_id = row[0]
    return run_id


def read_m4_client_summaries(run_id: str | None = None) -> tuple[str, list[dict[str, Any]]]:
    """
    Lightweight rows for CA picker: no large JSONB blobs in the bundle.
    Returns (resolved_run_id, [{memory_row_id, client_id, name, persona_tag, vip_tier}, ...]).
    Full memory is loaded per client at generation time (see fetch_m4_client_full_by_pk).
    """
    table_mode = os.environ.get("M5_MODULE4_TABLE", "visits").strip().lower()
    if table_mode in ("visits", "module4_client_visits", "latest"):
        source = (run_id or os.environ.get("M5_MODULE4_VISITS_SOURCE", "").strip()) or "module4_local_profile_json"
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, visit_id, client_name, customer_segment, source, saved_at "
            "FROM module4_client_visits WHERE source = %s "
            "ORDER BY saved_at DESC NULLS LAST, created_at DESC, id DESC",
            (source,),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        out: list[dict[str, Any]] = []
        for r in rows:
            db_id = r["id"]
            visit_id = (r.get("visit_id") or "").strip()
            out.append({
                "memory_row_id": db_id,
                "client_id": visit_id or f"m4_visit_{db_id}",
                "name": (r.get("client_name") or "").strip() or "Client (Module 4 Visit)",
                "persona_tag": (r.get("customer_segment") or "").strip() or "module4_client_visit",
                "vip_tier": "N/A",
                "source_table": "module4_client_visits",
                "module4_visit_id": visit_id,
                "saved_at": _ts(r.get("saved_at")),
            })
        return f"module4_client_visits:{source}", out

    conn = get_conn()
    cur = conn.cursor()
    rid = _resolve_m4_run_id(cur, run_id)
    cur.execute(
        "SELECT id, run_id, client_id, display_name, persona_tag, vip_tier "
        "FROM module4_client_memories WHERE run_id = %s ORDER BY id",
        (rid,),
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()

    out: list[dict[str, Any]] = []
    for r in rows:
        db_id = r["id"]
        rid_row = r["run_id"]
        cid = (r.get("client_id") or "").strip()
        if not cid:
            cid = f"m4_{rid_row}_{db_id}"
        name = (r.get("display_name") or "").strip() or "Client (Module 4)"
        ptag = (r.get("persona_tag") or "").strip() or "module4_structured_memory"
        vip = (r.get("vip_tier") or "").strip() or "N/A"
        out.append({
            "memory_row_id": db_id,
            "client_id": cid,
            "name": name,
            "persona_tag": ptag,
            "vip_tier": vip,
        })
    return rid, out


def fetch_m4_client_full_by_pk(m4_run_id: str, memory_row_id: int) -> dict[str, Any]:
    """Load one full client memory row for LLM context (tool-style on-demand fetch)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '15000ms'")
    if str(m4_run_id).startswith("module4_client_visits:"):
        cur.execute(
            "SELECT id, visit_id, client_name, customer_segment, saved_at, "
            "       raw_transcript_ca, summary, target_recipients, life_event, timeline, "
            "       aesthetic_preference, size_height, budget, mood, trend_signals, "
            "       next_step_intent, interested_items, client_constraints, "
            "       purchase_frequency, visit_purpose, purchase_decision_status, "
            "       positive_signals, negative_reasons, client_timeline, ca_action_item, "
            "       l1_client_profile, l2_constraints, l3_visit_funnel, l4_next_steps, "
            "       full_profile, source, created_at, updated_at "
            "FROM module4_client_visits WHERE id = %s",
            (memory_row_id,),
        )
        row = cur.fetchone()
        cols = [d[0] for d in cur.description]
        conn.close()
        if not row:
            raise ValueError(f"No module4_client_visits row for id={memory_row_id}")
        return _row_to_m5_visit_client(dict(zip(cols, row)))

    cur.execute(
        "SELECT id, run_id, client_id, display_name, persona_tag, vip_tier, "
        "       raw_voice_note, summary, life_event, timeline, "
        "       aesthetic_preference, size_height, budget, mood, trend_signals, "
        "       next_step_intent, model_used, confidence_summary, missing_fields_count, "
        "       generated_at "
        "FROM module4_client_memories WHERE run_id = %s AND id = %s",
        (m4_run_id, memory_row_id),
    )
    row = cur.fetchone()
    cols = [d[0] for d in cur.description]
    conn.close()
    if not row:
        raise ValueError(
            f"No module4_client_memories row for run_id={m4_run_id!r} id={memory_row_id}"
        )
    return _row_to_m5_client(dict(zip(cols, row)))


def read_module4_client_memories(run_id: str | None = None) -> dict[str, Any]:
    """
    Read rows from module4_client_memories (written by Module 4).
    If run_id is None, uses M5_MODULE4_RUN_ID or the latest run_id by generated_at.
    Returns: {"clients": [ {...}, ... ]} — each item is the real M4 memory shape for the LLM.
    """
    run_id = (run_id or os.environ.get("M5_MODULE4_RUN_ID", "").strip()) or None

    conn = get_conn()
    cur = conn.cursor()

    if run_id is None:
        cur.execute(
            "SELECT run_id FROM module4_client_memories "
            "ORDER BY generated_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            raise ValueError("No rows found in module4_client_memories.")
        run_id = row[0]

    cur.execute(
        "SELECT id, run_id, client_id, display_name, persona_tag, vip_tier, "
        "       raw_voice_note, summary, life_event, timeline, "
        "       aesthetic_preference, size_height, budget, mood, trend_signals, "
        "       next_step_intent, model_used, confidence_summary, missing_fields_count, "
        "       generated_at "
        "FROM module4_client_memories WHERE run_id = %s ORDER BY id",
        (run_id,),
    )
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()

    if not rows:
        raise ValueError(f"No module4_client_memories rows for run_id={run_id}.")

    clients = [_row_to_m5_client(r) for r in rows]
    return {"clients": clients}


if __name__ == "__main__":
    if not is_configured():
        print("Supabase not configured (SUPABASE_PASSWORD missing).")
        sys.exit(1)
    import json as _json
    print("── module2_trend_shortlist ──")
    try:
        ts = read_trend_shortlist()
        print(f"  trends: {len(ts['trends'])}  run={ts['query_context'].get('module2_run_id')}")
        print(_json.dumps(ts, ensure_ascii=False, indent=2)[:1200])
    except Exception as e:
        print(f"  ERROR: {e}")
    print("\n── module4_client_memories ──")
    try:
        cp = read_module4_client_memories()
        print(f"  clients: {len(cp['clients'])}")
        for c in cp["clients"]:
            print(f"  - {c['client_id']}  summary[:60]={str(c.get('summary',''))[:60]}")
    except Exception as e:
        print(f"  ERROR: {e}")
