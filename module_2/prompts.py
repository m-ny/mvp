"""
prompts.py — LLM prompt templates for Module 2 Trend Relevance & Materiality Filter Agent.
"""

import json

SYSTEM_PROMPT = """You are a senior luxury retail trend analyst specializing in Chinese consumer behavior on Xiaohongshu, with deep expertise in the Celine brand. You evaluate trend signals and decide which trends are truly material, brand-appropriate for Celine, and actionable for Celine Client Advisors. You are evidence-grounded and precise. You never shortlist a trend just because it is popular — it must reflect Celine's Parisian minimalism, quiet luxury, and intellectual femininity, match the Celine clientele of affluent design-conscious women who value craftsmanship over logos, and be usable in a real Celine clienteling conversation. You always cite specific snippets or metrics in your reasoning. You never write generic statements like 'this trend aligns with Celine values' without explaining exactly why with specific evidence from the trend object."""


def build_trend_evaluation_prompt(brand_profile: dict, trend_object: dict, today: str = "2026-03-25") -> str:
    """
    Build the per-trend evaluation prompt.
    Returns a string prompt ready to send to the LLM.
    """
    brand_profile_str = json.dumps(brand_profile, ensure_ascii=False, indent=2)
    trend_object_str = json.dumps(trend_object, ensure_ascii=False, indent=2)

    return f"""You are evaluating one trend object for Celine.

Brand Profile:
{brand_profile_str}

Trend Object:
{trend_object_str}

Today's date: {today}

Score this trend on these 5 dimensions (0–10 each). For each score you must cite specific evidence from the trend object — a snippet, a metric, a keyword, a date. Do not write generic reasoning.

Dimensions:

1. FRESHNESS (0–10): Is this trend still gaining traction as of today? Look at the dates in evidence.posts — are the most recent posts within the last 2 weeks? Is there a pattern of growing or fading momentum across the post dates?

2. BRAND FIT (0–10): Does this trend match Celine's Parisian minimalism and quiet luxury aesthetic? Does it match the Celine clientele — affluent women 28-50 who value craftsmanship over logos, design-consciousness, and understated elegance? Would a Celine CA feel genuinely comfortable raising this trend in a refined client conversation?

3. CATEGORY FIT (0–10): Is this trend appropriate for this specific product category? Ready-to-wear moves fast — recency and momentum matter most. Leather goods moves at medium pace — sustained signal across multiple weeks matters more than single viral moments.

4. MATERIALITY (0–10): Is total_engagement strong enough to be meaningful for a luxury brand audience on XHS? Is engagement spread across multiple posts rather than one viral outlier? Does post_count show real sustained interest over time?

5. ACTIONABILITY (0–10): Can a Celine CA mention this trend naturally in a refined, understated client conversation? Is it specific enough to be useful — something concrete a CA can reference with a specific Celine product or silhouette? Would an affluent Celine client respond positively and feel the CA is knowledgeable?

Compute composite_score as:
(freshness × 0.20) + (brand_fit × 0.30) + (category_fit × 0.20) + (materiality × 0.15) + (actionability × 0.15)

A trend is shortlisted ONLY if:
- composite_score >= 6.5
- No individual dimension score is below 4
- You judge it genuinely usable for Dior CAs right now

Return ONLY valid JSON with no markdown and no text outside the JSON:
{{
  "trend_id": "string",
  "shortlist": true or false,
  "scores": {{
    "freshness": number,
    "brand_fit": number,
    "category_fit": number,
    "materiality": number,
    "actionability": number
  }},
  "composite_score": number,
  "reasoning": "3-5 sentences, specific and evidence-grounded. Must cite at least one snippet or metric by name. Must explain why this is or is not right for Celine specifically.",
  "confidence": "high" or "medium" or "low",
  "evidence_references": ["direct quote or metric from the trend object that supports the decision"],
  "disqualifying_reason": null or "exact dimension that failed and why"
}}"""


def build_batch_evaluation_prompt(brand_profile: dict, trend_objects: list, today: str = "2026-03-25") -> str:
    """
    Build a batch evaluation prompt for up to 5 trend objects at once.
    Returns a prompt asking the LLM to return a JSON array of evaluations.
    """
    brand_profile_str = json.dumps(brand_profile, ensure_ascii=False, indent=2)
    trends_str = json.dumps(trend_objects, ensure_ascii=False, indent=2)

    return f"""You are evaluating a batch of trend objects for Celine.

Brand Profile:
{brand_profile_str}

Today's date: {today}

Trend Objects (batch of {len(trend_objects)}):
{trends_str}

For EACH trend object in the batch, score it on these 5 dimensions (0–10 each). For each score you must cite specific evidence from that trend object — a snippet, a metric, a keyword, a date. Do not write generic reasoning.

Dimensions:

1. FRESHNESS (0–10): Is this trend still gaining traction as of today? Look at the dates in evidence.posts — are the most recent posts within the last 2 weeks? Is there a pattern of growing or fading momentum across the post dates?

2. BRAND FIT (0–10): Does this trend match Celine's Parisian minimalism and quiet luxury aesthetic? Does it match the Celine clientele — affluent women 28-50 who value craftsmanship over logos and understated elegance? Would a Celine CA feel genuinely comfortable raising this trend in a refined client conversation?

3. CATEGORY FIT (0–10): Is this trend appropriate for this specific product category? Ready-to-wear moves fast — recency and momentum matter most. Leather goods moves at medium pace — sustained signal across multiple weeks matters more than single viral moments.

4. MATERIALITY (0–10): Is total_engagement strong enough to be meaningful for a luxury brand audience on XHS? Is engagement spread across multiple posts rather than one viral outlier? Does post_count show real sustained interest over time?

5. ACTIONABILITY (0–10): Can a Celine CA mention this trend naturally in a refined, understated client conversation? Is it specific enough to be useful — something concrete a CA can reference with a specific Celine product or silhouette? Would an affluent Celine client respond positively and feel the CA is knowledgeable?

Compute composite_score as:
(freshness × 0.20) + (brand_fit × 0.30) + (category_fit × 0.20) + (materiality × 0.15) + (actionability × 0.15)

A trend is shortlisted ONLY if:
- composite_score >= 6.5
- No individual dimension score is below 4
- You judge it genuinely usable for Dior CAs right now

Return ONLY a valid JSON array with no markdown and no text outside the JSON. One object per trend, in the same order as the input batch:
[
  {{
    "trend_id": "string",
    "shortlist": true or false,
    "scores": {{
      "freshness": number,
      "brand_fit": number,
      "category_fit": number,
      "materiality": number,
      "actionability": number
    }},
    "composite_score": number,
    "reasoning": "3-5 sentences, specific and evidence-grounded. Must cite at least one snippet or metric by name. Must explain why this is or is not right for Celine specifically.",
    "confidence": "high" or "medium" or "low",
    "evidence_references": ["direct quote or metric from the trend object that supports the decision"],
    "disqualifying_reason": null or "exact dimension that failed and why"
  }}
]"""
