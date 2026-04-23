"""
run_atypica_refresh.py — Manually trigger Atypica brand profile refresh.

Calls Atypica API for brand profile and consumer personas, structures the
result with LLM, saves to module_2/brand_profile_{brand}.json.

Usage:
    cd /Users/kellyliu/Desktop/mvp_W10
    python module_2/run_atypica_refresh.py Tiffany
    python module_2/run_atypica_refresh.py "Louis Vuitton"
    python module_2/run_atypica_refresh.py            # defaults to Tiffany
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
from atypica_client import get_or_refresh_brand_data, _brand_slug, _profile_path


def main():
    brand_name = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Tiffany"

    print("=" * 60)
    print(f"Atypica Brand Profile Refresh")
    print(f"Brand: {brand_name}")
    print(f"Output: module_2/brand_profile_{_brand_slug(brand_name)}.json")
    print("=" * 60)

    try:
        brand_profile = get_or_refresh_brand_data(brand_name, force_refresh=True)
    except Exception as e:
        print(f"\n[ERROR] Refresh failed: {e}")
        sys.exit(1)

    # Pretty-print summary
    print(f"\n{'─'*60}")
    print(f"BRAND PROFILE SUMMARY")
    print(f"{'─'*60}")
    print(f"  Brand name:       {brand_profile.get('brand_name')}")
    print(f"  Chinese name:     {brand_profile.get('brand_name_cn')}")
    print(f"  Director:         {brand_profile.get('current_creative_director')}")
    print(f"  Aesthetic DNA:    {str(brand_profile.get('aesthetic_dna', ''))[:120]}...")
    print(f"  Active categories:{brand_profile.get('active_categories')}")

    archetypes = brand_profile.get("client_archetypes", [])
    print(f"\n  Client archetypes ({len(archetypes)} total):")
    for a in archetypes:
        print(
            f"    • {a.get('name')} ({a.get('age_range')}) "
            f"— budget ¥{a.get('entry_budget_rmb', '?'):,}–¥{a.get('stretch_budget_rmb', '?'):,}"
        )

    hero = brand_profile.get("hero_products", {})
    print(f"\n  Hero products ({len(hero)} collections):")
    for coll, items in hero.items():
        if isinstance(items, list):
            print(f"    {coll}: {', '.join(items[:2])}" + (" ..." if len(items) > 2 else ""))

    pillars = brand_profile.get("aesthetic_pillars", [])
    print(f"\n  Aesthetic pillars ({len(pillars)}):")
    for p in pillars:
        print(f"    • {p.get('name')}: {str(p.get('description', ''))[:80]}")

    saved_path = _profile_path(brand_name)
    print(f"\n{'─'*60}")
    print(f"Saved to: {saved_path}")
    print(f"File size: {saved_path.stat().st_size:,} bytes")
    print(f"{'─'*60}\n")


if __name__ == "__main__":
    main()
