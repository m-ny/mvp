"""
verify_supabase.py — Verify module2_trend_shortlist schema and data.

Prints:
  1. All column names in module2_trend_shortlist
  2. Total row count
  3. 3 most recent rows (key fields only)
  4. data_type distribution
  5. Archetype distribution (client_persona_match_name)
  6. Subcategory distribution

Usage:
    cd /Users/kellyliu/Desktop/mvp_W10
    python module_2/verify_supabase.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from supabase_client import get_conn, is_configured


def run_verification():
    if not is_configured():
        print("[ERROR] SUPABASE_PASSWORD not set — check your .env file.")
        sys.exit(1)

    conn = get_conn()
    print("\n" + "=" * 60)
    print("Supabase Verification — module2_trend_shortlist")
    print("=" * 60)

    try:
        with conn.cursor() as cur:

            # ── 1. Column names ───────────────────────────────────────────
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'module2_trend_shortlist'
                ORDER BY ordinal_position;
            """)
            cols = cur.fetchall()
            print(f"\n1. COLUMNS ({len(cols)} total):")
            for col_name, dtype in cols:
                print(f"   {col_name:<40s} {dtype}")

            # ── 2. Row count ──────────────────────────────────────────────
            cur.execute("SELECT COUNT(*) FROM module2_trend_shortlist;")
            total = cur.fetchone()[0]
            print(f"\n2. TOTAL ROWS: {total}")

            # ── 3. 3 most recent rows ─────────────────────────────────────
            cur.execute("""
                SELECT run_id, trend_id, label, composite_score,
                       data_type, client_persona_match_name,
                       hero_product, subcategory, created_at
                FROM module2_trend_shortlist
                ORDER BY created_at DESC
                LIMIT 3;
            """)
            recent = cur.fetchall()
            print(f"\n3. 3 MOST RECENT ROWS:")
            for row in recent:
                run_id, trend_id, label, score, dtype, archetype, hero, subcat, ts = row
                print(f"   [{trend_id}] {(label or '')[:45]}")
                print(f"     score={score}  type={dtype}  archetype={archetype}")
                print(f"     hero={hero}  subcat={subcat}")
                print(f"     run={run_id}  at={ts}")

            # ── 4. data_type distribution ─────────────────────────────────
            cur.execute("""
                SELECT COALESCE(data_type, 'null') AS dtype, COUNT(*) AS n
                FROM module2_trend_shortlist
                GROUP BY dtype
                ORDER BY n DESC;
            """)
            dist = cur.fetchall()
            print(f"\n4. DATA_TYPE DISTRIBUTION:")
            for dtype, n in dist:
                print(f"   {dtype:<20s} {n} rows")

            # ── 5. Archetype distribution ─────────────────────────────────
            cur.execute("""
                SELECT COALESCE(client_persona_match_name, '(none)') AS archetype,
                       COUNT(*) AS n
                FROM module2_trend_shortlist
                GROUP BY archetype
                ORDER BY n DESC;
            """)
            archetypes = cur.fetchall()
            print(f"\n5. ARCHETYPE DISTRIBUTION:")
            for archetype, n in archetypes:
                print(f"   {archetype:<40s} {n} rows")

            # ── 6. Subcategory distribution ───────────────────────────────
            cur.execute("""
                SELECT COALESCE(subcategory, '(none)') AS subcat, COUNT(*) AS n
                FROM module2_trend_shortlist
                GROUP BY subcat
                ORDER BY n DESC;
            """)
            subcats = cur.fetchall()
            print(f"\n6. SUBCATEGORY DISTRIBUTION:")
            for subcat, n in subcats:
                print(f"   {subcat:<30s} {n} rows")

        print("\n" + "=" * 60)
        print("Verification complete.")
        print("=" * 60 + "\n")

    finally:
        conn.close()


if __name__ == "__main__":
    run_verification()
