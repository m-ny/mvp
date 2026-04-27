#!/usr/bin/env python3
"""
Export Module 5 inputs to one JSON file for offline runs (no Supabase reads for M2/M4/M1).

Run once while online (with SUPABASE_PASSWORD + same env as normal M5):

  cd /path/to/m-ny-mvp
  python3 module_5/export_offline_snapshot.py
  # or:
  python3 module_5/export_offline_snapshot.py -o module_5/_offline/m5_input_snapshot.json

Then run M5 with:

  export M5_OFFLINE_SNAPSHOT=module_5/_offline/m5_input_snapshot.json
  python3 -u module_5/agent.py --all --from-index 1 --to-index 2

You still need OPENROUTER_API_KEY (or ANTHROPIC_API_KEY) for the LLM.
Writing results to Supabase is optional; omit SUPABASE_PASSWORD for fully offline output to run_log.json only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
import config  # noqa: F401

from module_1.supabase_reader import read_brand_products
from module_5.supabase_reader import (
    fetch_m4_client_full_by_pk,
    read_m4_client_summaries,
    read_trend_shortlist,
)


def _json_safe(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, str, int, float)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    return str(obj)


def main() -> None:
    p = argparse.ArgumentParser(description="Export M2/M4/M1 to one JSON for offline M5")
    p.add_argument(
        "-o",
        "--output",
        default="module_5/_offline/m5_input_snapshot.json",
        help="Output path (relative to repo root unless absolute)",
    )
    args = p.parse_args()

    from supabase_client import is_configured

    if not is_configured():
        print("ERROR: SUPABASE_PASSWORD not set; cannot export from database.", file=sys.stderr)
        sys.exit(1)

    brand = (os.environ.get("BRAND") or "").strip() or config.BRAND
    os.environ["BRAND"] = brand
    data_source = (os.environ.get("M5_CATALOG_DATA_SOURCE") or "").strip() or None

    print("Exporting M2 trend shortlist…")
    trends_data = read_trend_shortlist()
    if not (trends_data.get("trends") or []):
        print("ERROR: No M2 trends returned.", file=sys.stderr)
        sys.exit(1)

    print("Exporting M4 client list + full visit rows…")
    m4_run_id, summaries = read_m4_client_summaries()
    clients_full: list[dict[str, Any]] = []
    for s in summaries:
        rid = int(s["memory_row_id"])
        clients_full.append(_json_safe(fetch_m4_client_full_by_pk(m4_run_id, rid)))
    if not clients_full:
        print("ERROR: No M4 clients exported.", file=sys.stderr)
        sys.exit(1)

    print("Exporting M1 brand products…")
    catalog_rows = _json_safe(read_brand_products(brand=brand, data_source=data_source))

    bundle = {
        "version": 1,
        "exported_at": datetime.now().astimezone().isoformat(),
        "brand": brand,
        "module4_run_id": m4_run_id,
        "module2_run_id": (trends_data.get("query_context") or {}).get("module2_run_id"),
        "m4_visits_source": (os.environ.get("M5_MODULE4_VISITS_SOURCE") or "module4_local_profile_json").strip(),
        "m4_table_mode": (os.environ.get("M5_MODULE4_TABLE") or "visits").strip(),
        "trends_data": _json_safe(trends_data),
        "clients_full": clients_full,
        "catalog_rows": catalog_rows,
    }

    out = Path(args.output)
    if not out.is_absolute():
        out = (_REPO / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"  trends:   {len(trends_data.get('trends') or [])}")
    print(f"  clients:  {len(clients_full)}")
    print(f"  catalog:  {len(catalog_rows)}  ({brand})")
    print()
    print("Offline M5:")
    try:
        rel = out.relative_to(_REPO)
        print(f"  export M5_OFFLINE_SNAPSHOT={rel}")
    except ValueError:
        print(f"  export M5_OFFLINE_SNAPSHOT={out}")


if __name__ == "__main__":
    main()
