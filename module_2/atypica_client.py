"""
atypica_client.py — Atypica API client for dynamic brand profile and persona generation.

Workflow:
  1. POST /api/study with research query → returns study_id
  2. Poll GET /api/study/{study_id} until status = "complete"
  3. Extract report text from response
  4. Use OpenRouter LLM to structure text into brand profile JSON schema
  5. Cache result to module_2/brand_profile_{slug}.json with timestamp

Falls back gracefully to existing static JSON if:
  - ATYPICA_API_KEY is not set
  - API call fails or times out
  - LLM structuring fails

Usage:
    from atypica_client import get_or_refresh_brand_data
    brand_profile = get_or_refresh_brand_data("Tiffany")
    brand_profile = get_or_refresh_brand_data("Tiffany", force_refresh=True)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# ── Config ──────────────────────────────────────────────────────────────────────
ATYPICA_API_BASE = "https://atypica.ai/api"
CACHE_MAX_AGE_DAYS = 7
POLL_INTERVAL_SEC = 3
POLL_MAX_ATTEMPTS = 60          # 3 minutes maximum wait per study
BASE_DIR = Path(__file__).parent


# ── Slug helpers ─────────────────────────────────────────────────────────────────

def _brand_slug(brand_name: str) -> str:
    """Convert brand name to lowercase filesystem slug. e.g. 'Tiffany & Co.' → 'tiffany'"""
    return (
        brand_name.lower()
        .strip()
        .split("&")[0]          # drop "& Co." suffix
        .strip()
        .replace(" ", "_")
        .replace(".", "")
        .replace(",", "")
        .rstrip("_")
    )


def _profile_path(brand_name: str) -> Path:
    return BASE_DIR / f"brand_profile_{_brand_slug(brand_name)}.json"


# ── Cache freshness ──────────────────────────────────────────────────────────────

def _is_cache_fresh(brand_name: str) -> bool:
    """Return True if the cached profile file exists and is younger than CACHE_MAX_AGE_DAYS."""
    path = _profile_path(brand_name)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at_str = data.get("_cached_at")
        if not cached_at_str:
            return False
        cached_at = datetime.fromisoformat(cached_at_str)
        age = datetime.now(timezone.utc) - cached_at.replace(tzinfo=timezone.utc)
        return age < timedelta(days=CACHE_MAX_AGE_DAYS)
    except Exception:
        return False


def _load_static(brand_name: str) -> Optional[dict]:
    """Load static brand profile JSON, strip internal _cached_at key before returning."""
    path = _profile_path(brand_name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.pop("_cached_at", None)
        return data
    except Exception:
        return None


# ── Atypica API calls ────────────────────────────────────────────────────────────

def _get_atypica_key() -> str:
    return os.environ.get("ATYPICA_API_KEY", "")


def _post_study(query: str, api_key: str) -> str:
    """POST a new Atypica study and return the study_id."""
    try:
        import requests
    except ImportError:
        raise ImportError("requests package required — run: pip install requests")

    resp = requests.post(
        f"{ATYPICA_API_BASE}/study",
        json={"message": query},
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    study_id = data.get("study_id") or data.get("id") or data.get("studyId")
    if not study_id:
        raise ValueError(f"Atypica did not return a study_id: {data}")
    return str(study_id)


def _poll_study(study_id: str, api_key: str) -> str:
    """Poll Atypica until study completes. Returns report text."""
    try:
        import requests
    except ImportError:
        raise ImportError("requests package required — run: pip install requests")

    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL_SEC)
        resp = requests.get(
            f"{ATYPICA_API_BASE}/study/{study_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = (data.get("status") or "").lower()

        if status in ("complete", "completed", "done", "finished", "success"):
            text = (
                data.get("report")
                or data.get("content")
                or data.get("result")
                or data.get("output")
                or data.get("text")
                or ""
            )
            print(f"  [Atypica] Study {study_id} complete ({attempt * POLL_INTERVAL_SEC}s)")
            return str(text)

        if status in ("error", "failed", "failure"):
            raise RuntimeError(f"Atypica study {study_id} failed with status '{status}': {data}")

        if attempt % 5 == 0:
            print(f"  [Atypica] Waiting for study {study_id} (status={status}, {attempt * POLL_INTERVAL_SEC}s)...")

    raise TimeoutError(
        f"Atypica study {study_id} did not complete within "
        f"{POLL_MAX_ATTEMPTS * POLL_INTERVAL_SEC} seconds"
    )


def _call_atypica(query: str) -> str:
    """Create a study, poll for completion, return report text."""
    api_key = _get_atypica_key()
    if not api_key:
        raise EnvironmentError("ATYPICA_API_KEY not set")
    print(f"  [Atypica] Posting study...")
    study_id = _post_study(query, api_key)
    print(f"  [Atypica] Study ID: {study_id} — polling...")
    return _poll_study(study_id, api_key)


# ── LLM-based JSON structuring ───────────────────────────────────────────────────

_SCHEMA_HINT = """
{
  "brand_name": "string",
  "brand_name_cn": "Chinese brand name",
  "current_creative_director": "string",
  "aesthetic_dna": "1-2 sentence description",
  "current_direction": "1-2 sentence description of current strategy",
  "brand_voice": "adjectives describing brand tone",
  "active_categories": ["list of product category strings"],
  "client_archetypes": [
    {
      "name": "Chinese + pinyin name",
      "age_range": "XX-XX",
      "lifestyle": "string",
      "aspiration": "string",
      "occupation": "string",
      "typical_budget_rmb": number,
      "entry_budget_rmb": number,
      "stretch_budget_rmb": number,
      "trend_language_that_resonates": "string",
      "what_they_would_never_buy": "string",
      "purchase_motivations": ["list"],
      "occasion_triggers": ["list"],
      "preferred_collections": ["list"]
    }
  ],
  "hero_products": {
    "collection_name": ["Product Name (¥price range)"]
  },
  "budget_tiers": {
    "entry": {"range_rmb": "¥X-Y", "products": [], "ca_angle": "string"},
    "core": {"range_rmb": "¥X-Y", "products": [], "ca_angle": "string"},
    "aspirational": {"range_rmb": "¥X-Y", "products": [], "ca_angle": "string"},
    "investment": {"range_rmb": "¥X+", "products": [], "ca_angle": "string"}
  },
  "aesthetic_pillars": [
    {"name": "string", "description": "one sentence"}
  ],
  "competitive_differentiation": {
    "competitor_brand": "how brand differs from this competitor"
  },
  "brand_taboos": {
    "category_taboos": ["keyword list"]
  }
}
"""


def _structure_with_llm(brand_name: str, profile_text: str, personas_text: str) -> dict:
    """
    Call OpenRouter LLM to parse raw Atypica text into structured brand profile JSON.
    Returns empty dict on any failure (caller will merge with static fallback).
    """
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not openrouter_key:
        print("  [Atypica] OPENROUTER_API_KEY not set — cannot structure response")
        return {}

    try:
        from openai import OpenAI
    except ImportError:
        print("  [Atypica] openai package not installed — cannot structure response")
        return {}

    client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
    model = os.environ.get("DEFAULT_MODEL", "anthropic/claude-3-5-sonnet")

    # Truncate inputs to stay within token limits
    profile_excerpt = profile_text[:6000]
    personas_excerpt = personas_text[:6000]

    prompt = f"""You are extracting structured brand data from research reports about {brand_name} for a luxury retail AI agent.

BRAND PROFILE REPORT (from Atypica):
{profile_excerpt}

CONSUMER PERSONAS REPORT (from Atypica):
{personas_excerpt}

Extract this information into a valid JSON object matching this schema exactly:
{_SCHEMA_HINT}

Rules:
- Include ALL consumer personas found in the report — do not cap or limit
- Use Chinese + pinyin format for persona names where applicable
- Price ranges should be in RMB (¥)
- active_categories should include "luxury_jewelry" for jewelry brands
- Return ONLY the JSON object, no markdown, no explanation

JSON:"""

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()
        parsed = json.loads(raw)
        print(f"  [Atypica] Structured {len(parsed.get('client_archetypes', []))} archetypes from LLM")
        return parsed
    except Exception as e:
        print(f"  [Atypica] LLM structuring failed: {e}")
        return {}


# ── Public API ───────────────────────────────────────────────────────────────────

def get_brand_profile(brand_name: str) -> str:
    """
    Call Atypica to research brand positioning, hero products, and voice.
    Returns raw report text.
    """
    query = (
        f"What is {brand_name}'s current aesthetic positioning, hero products with price ranges "
        f"in RMB, key collections, competitive differentiation vs other luxury brands, brand taboos, "
        f"and brand voice for the Chinese luxury market in 2026?"
    )
    return _call_atypica(query)


def get_consumer_personas(brand_name: str) -> str:
    """
    Call Atypica to generate all consumer personas for the brand in China.
    Returns raw report text.
    """
    query = (
        f"Generate ALL relevant consumer personas for {brand_name} customers in China's luxury market. "
        f"Do not limit the number — include every distinct consumer segment that meaningfully interacts "
        f"with this brand across China. For each persona include: name, age range, lifestyle, occupation, "
        f"typical budget in RMB, entry budget, typical budget, stretch budget, purchase motivations, "
        f"occasion triggers, XHS behavior, what content resonates, what they value in a CA interaction, "
        f"aesthetic preferences, which specific collections they prefer, competitor brands they consider, "
        f"and what makes them choose {brand_name}."
    )
    return _call_atypica(query)


def get_or_refresh_brand_data(brand_name: str, force_refresh: bool = False) -> dict:
    """
    Return a complete brand profile dict for brand_name.

    Cache logic:
      - If cached file exists and is < 7 days old AND force_refresh=False: return cached.
      - Otherwise: call Atypica for brand profile + consumer personas, structure with LLM,
        merge with static fallback JSON, save to brand_profile_{slug}.json with timestamp.

    Fallback:
      - If ATYPICA_API_KEY not set or any API/LLM step fails:
        loads and returns existing static JSON and prints a warning.
    """
    slug = _brand_slug(brand_name)
    path = _profile_path(brand_name)

    # Return fresh cache if available
    if not force_refresh and _is_cache_fresh(brand_name):
        print(f"[Atypica] Using cached brand profile for {brand_name} ({path.name})")
        return _load_static(brand_name) or {}

    # Attempt Atypica refresh
    api_key = _get_atypica_key()
    if not api_key:
        print(f"[Atypica] ATYPICA_API_KEY not set — using cached brand profile for {brand_name}")
        static = _load_static(brand_name)
        if static:
            return static
        raise FileNotFoundError(
            f"No cached brand profile found at {path} and ATYPICA_API_KEY is not set. "
            f"Create {path} manually or set ATYPICA_API_KEY."
        )

    print(f"\n[Atypica] Refreshing brand data for {brand_name}...")
    profile_text = ""
    personas_text = ""

    try:
        print("[Atypica] Step 1/2 — fetching brand profile...")
        profile_text = get_brand_profile(brand_name)
    except Exception as e:
        print(f"[Atypica] Brand profile fetch failed: {e}")

    try:
        print("[Atypica] Step 2/2 — fetching consumer personas...")
        personas_text = get_consumer_personas(brand_name)
    except Exception as e:
        print(f"[Atypica] Consumer personas fetch failed: {e}")

    if not profile_text and not personas_text:
        print(f"[Atypica] Both API calls failed — using cached brand profile for {brand_name}")
        static = _load_static(brand_name)
        if static:
            return static
        raise RuntimeError(f"Atypica API unavailable and no cached profile found for {brand_name}")

    # Structure the text into JSON with LLM
    structured = _structure_with_llm(brand_name, profile_text, personas_text)

    # Merge: static fallback provides defaults; structured overrides where present
    base = _load_static(brand_name) or {}
    merged = {**base, **{k: v for k, v in structured.items() if v}}

    # Ensure required fields
    merged.setdefault("brand_name", brand_name)
    merged.setdefault("active_categories", ["luxury_jewelry", "luxury_fashion"])

    # Store raw Atypica text for reference
    merged["_atypica_profile_raw"] = profile_text[:2000] if profile_text else ""
    merged["_atypica_personas_raw"] = personas_text[:2000] if personas_text else ""
    merged["_cached_at"] = datetime.now(timezone.utc).isoformat()
    merged["_source"] = "atypica_api"

    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Atypica] Brand profile saved → {path}")

    # Return clean version (strip internal keys)
    clean = {k: v for k, v in merged.items() if not k.startswith("_")}
    return clean
