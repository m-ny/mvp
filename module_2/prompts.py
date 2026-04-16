"""
prompts.py — LLM prompt templates for Module 2 Trend Relevance & Materiality Filter Agent.

Brand name and profile details are injected at runtime from brand_profile_{brand}.json.
All archetype names, hero products, collections, budget tiers, and pillars are read
dynamically — nothing is hardcoded. Supports any brand loaded via atypica_client.
"""

import json


def build_system_prompt(brand_profile: dict) -> str:
    brand_name = brand_profile.get("brand_name", "the brand")
    aesthetic = brand_profile.get("aesthetic_dna", brand_profile.get("aesthetic", "luxury"))
    tone = brand_profile.get("clienteling_tone", "precise, expert, refined")
    voice = brand_profile.get("brand_voice", "confident and refined")
    director = brand_profile.get("current_creative_director", "")
    director_str = f" under {director}" if director else ""

    archetypes = brand_profile.get("client_archetypes", [])
    archetype_count = len(archetypes)
    archetype_names = [a.get("name", "") for a in archetypes]
    archetype_str = ", ".join(archetype_names) if archetype_names else "the brand's target clients"

    return (
        f"You are a senior luxury retail trend analyst specialising in Chinese consumer behaviour "
        f"on Xiaohongshu, with deep expertise in {brand_name}{director_str}. "
        f"You evaluate trend signals and decide which trends are truly material, brand-appropriate, "
        f"and actionable for {brand_name} Client Advisors in Shanghai. "
        f"You are evidence-grounded and precise. "
        f"\n\n"
        f"{brand_name} aesthetic: {aesthetic}. "
        f"Clienteling tone: {tone}. "
        f"Brand voice: {voice}. "
        f"\n\n"
        f"This brand has {archetype_count} client archetypes: {archetype_str}. "
        f"You will receive the full archetype list in each evaluation prompt. "
        f"You must match trends to one of these exact named archetypes — never invent a new one. "
        f"\n\n"
        f"You never shortlist a trend just because it is popular — it must reflect {brand_name}'s "
        f"specific aesthetic, match at least one named client archetype, and be genuinely usable "
        f"in a {brand_name} CA conversation within the next 7 days. "
        f"You always cite specific snippets or metrics in your reasoning. "
        f"You never write generic statements like 'this aligns with {brand_name} values' "
        f"without explaining exactly why with specific evidence from the trend object."
    )


def build_batch_evaluation_prompt(
    brand_profile: dict,
    trend_objects: list,
    today: str = "2026-04-16",
) -> str:
    """
    Build a batch evaluation prompt for up to 5 trend objects.
    All brand context (archetypes, products, collections, budget tiers, pillars,
    competitive positioning) is injected from brand_profile — fully dynamic.
    """
    brand_name = brand_profile.get("brand_name", "the brand")

    # ── Client archetypes block (dynamic — no hardcoded count) ─────────────────
    archetypes = brand_profile.get("client_archetypes", [])
    archetype_lines = []
    for a in archetypes:
        budget_line = ""
        if a.get("entry_budget_rmb"):
            budget_line = (
                f" | Budget: ¥{a.get('entry_budget_rmb'):,}–¥{a.get('stretch_budget_rmb'):,}"
            )
        archetype_lines.append(
            f"  • {a['name']} ({a.get('age_range', '')}): {a.get('lifestyle', '')} "
            f"| Responds to: {a.get('trend_language_that_resonates', '')} "
            f"| Preferred collections: {', '.join(a.get('preferred_collections', [])[:3])}"
            f"{budget_line}"
            f" | Would never buy: {a.get('what_they_would_never_buy', '')}"
        )
    archetype_block = (
        f"CLIENT ARCHETYPES — {len(archetypes)} segments "
        f"(you MUST use one of these exact names in matched_archetype):\n"
        + "\n".join(archetype_lines)
    ) if archetype_lines else ""

    archetype_names = [a.get("name", "") for a in archetypes]
    archetype_names_str = ", ".join(archetype_names) if archetype_names else "the target clients"

    # ── Hero products + budget tiers block ────────────────────────────────────
    hero_products = brand_profile.get("hero_products", {})
    budget_tiers = brand_profile.get("budget_tiers", {})

    if hero_products and isinstance(hero_products, dict):
        hero_lines = [
            f"  {cat.replace('_', ' ').title()}: {', '.join(items)}"
            for cat, items in hero_products.items()
            if isinstance(items, list)
        ]
        hero_block = (
            f"CURRENT HERO PRODUCTS WITH PRICE RANGES\n"
            f"(use these to populate hero_product_link and budget recommendations):\n"
            + "\n".join(hero_lines)
        )
    else:
        hero_block = ""

    if budget_tiers and isinstance(budget_tiers, dict):
        tier_lines = [
            f"  {tier.upper()} ({info.get('range_rmb', '')}): "
            f"{', '.join(info.get('products', [])[:2])} — CA angle: {info.get('ca_angle', '')}"
            for tier, info in budget_tiers.items()
            if isinstance(info, dict)
        ]
        tier_block = (
            "BUDGET TIERS (map matched archetype's budget to correct tier for product recommendations):\n"
            + "\n".join(tier_lines)
        )
    else:
        tier_block = ""

    # ── Aesthetic pillars block ────────────────────────────────────────────────
    pillars = brand_profile.get("aesthetic_pillars", [])
    if pillars:
        pillar_lines = [
            f"  • {p['name']}: {p.get('description', '')}" for p in pillars
        ]
        pillar_block = (
            "AESTHETIC PILLARS (compare against these when scoring novelty):\n"
            + "\n".join(pillar_lines)
        )
        pillar_names = [p.get("name", "") for p in pillars]
    else:
        pillar_block = ""
        pillar_names = []

    pillar_names_str = ", ".join(pillar_names) if pillar_names else "the brand's aesthetic pillars"

    # ── Competitive context ────────────────────────────────────────────────────
    competitive = brand_profile.get("competitive_differentiation", {})
    if competitive:
        comp_lines = [f"  vs {k}: {v}" for k, v in competitive.items()]
        comp_note = "COMPETITIVE POSITIONING (use when scoring brand_fit and novelty):\n" + "\n".join(comp_lines)
    else:
        comp_note = ""

    trends_str = json.dumps(trend_objects, ensure_ascii=False, indent=2)

    return f"""You are evaluating a batch of trend objects for {brand_name}.

Today's date: {today}

{archetype_block}

{hero_block}

{tier_block}

{pillar_block}

{comp_note}

Trend Objects (batch of {len(trend_objects)}):
{trends_str}

──────────────────────────────────────────────────────────────
SCORING INSTRUCTIONS

For EACH trend object, score it on the 6 LLM dimensions below (0–10 each).
For EVERY score you must cite specific evidence — a snippet, a metric, a keyword. No generic reasoning.

DIMENSIONS:

1. BRAND_FIT (0–10)
Does this trend match {brand_name}'s aesthetic DNA? Does it fit at least one named archetype's lifestyle? Would a {brand_name} CA feel genuinely comfortable raising it?
Use competitive context: if this trend is more relevant to a competitor's positioning, score low.
Cite a specific snippet or metric.

2. CA_CONVERSATIONAL_UTILITY (0–10)
Can a {brand_name} CA use this trend to open a client conversation and link it to a real product within 7 days?

IMPORTANT: Check the trend for an "extracted_product" field — this means a product name was found organically in real XHS posts. If present, reference it directly in reasoning and hero_product_link.
If NOT present, do NOT invent a product name. Use hero_product_link only if you can genuinely infer it from the trend. Leave it null if unsure.

Score 8–10: trend has an extracted_product, OR unmistakably implies a specific {brand_name} hero product by name.
Score 6–7: trend is clearly linkable to a specific {brand_name} product collection (e.g. engagement ring trend → Tiffany Setting; self-purchase bracelet trend → HardWear). No stretch required.
Score 4–5: trend is brand-relevant but the CA needs to work to connect it to a product — the link is real but not immediate.
Score 1–3: purely aesthetic or abstract — no plausible {brand_name} product category connection.

3. LANGUAGE_SPECIFICITY (0–10)
Are the XHS snippets using specific, vivid, quotable Chinese language a CA could echo to a client?
Score 8–10: snippets contain specific emotional or cultural references that feel authentic and reusable. Quote the most specific snippet.
Score 1–4: snippets are generic luxury descriptors with no distinctive voice.

4. CLIENT_PERSONA_MATCH (0–10)
Based on the {len(archetypes)} client archetypes listed above, how strongly does this trend resonate with at least one of them?
You MUST name the single best-matching archetype in matched_archetype (use the exact name string).
Score 8–10: extremely strong match — explain exactly why this specific archetype would respond, citing their lifestyle, budget, and occasion triggers.
Score 5–7: moderate match — identifiable archetype but the connection requires some inference.
Score 1–4: does not clearly match any named archetype's language, budget, lifestyle, or aspiration.

5. NOVELTY (0–10)
Is this trend saying something genuinely new about how {brand_name}'s customers engage with the brand in China?
Compare against these pillars: {pillar_names_str}.
Score 7–10: offers a new specific cultural insight, new occasion trigger, or new product usage pattern not captured in existing pillars.
Score 1–4: purely confirms an existing pillar without adding a new angle.
Always name the pillar being confirmed or extended in matched_pillar.

6. CATEGORY_FIT (0–10)
Is this trend appropriate for this jewelry category? Rings and bracelets move with occasion triggers. Necklaces respond to daily-wear trends. Engagement jewelry has distinct seasonal peaks.
Cite the specific jewelry category and explain the fit.

NOTE: trend_velocity and cross_run_persistence are computed algorithmically from engagement_recency_pct and run_count. Do NOT score these yourself.

──────────────────────────────────────────────────────────────
BUDGET-MATCHED PRODUCT RECOMMENDATIONS

For each shortlisted trend, recommend one specific {brand_name} product per budget tier based on:
1. The matched_archetype's typical budget (see archetype list above)
2. The trend's content angle (gifting? self-purchase? milestone?)
3. The hero products and budget tiers listed above

Fill these three fields for every trend (shortlisted or not — fill null if not relevant):
- recommended_product_entry: the best entry-tier {brand_name} piece for this trend (¥3,000–8,000 range)
- recommended_product_core: the best core-tier piece (¥8,000–30,000 range)
- recommended_product_stretch: the best stretch or aspirational piece (¥30,000+ range)

These recommendations help CAs have a prepared answer at every budget level, not just the primary archetype's budget.

──────────────────────────────────────────────────────────────
COMPOSITE SCORE FORMULA (for reference only — system will recompute)
brand_fit×0.20 + ca_conversational_utility×0.20 + trend_velocity×0.15 + language_specificity×0.15 + client_persona_match×0.10 + novelty×0.10 + category_fit×0.05 + cross_run_persistence×0.05

SHORTLISTING CRITERIA
Shortlist ONLY if:
- All 6 LLM-scored dimensions >= 4 (ca_conversational_utility minimum = 4)
- composite_score >= 6.5 (system will recompute, but use this as your guide)
- Genuinely usable for {brand_name} CAs right now

──────────────────────────────────────────────────────────────
OUTPUT FORMAT

Return ONLY a valid JSON array — no markdown, no text outside the JSON. One object per trend, same order as input batch:
[
  {{
    "trend_id": "string",
    "shortlist": true or false,
    "scores": {{
      "brand_fit": number,
      "ca_conversational_utility": number,
      "language_specificity": number,
      "client_persona_match": number,
      "novelty": number,
      "category_fit": number
    }},
    "matched_archetype": "exact archetype name string from the list above, or null",
    "matched_pillar": "name of the aesthetic pillar this trend confirms or extends, or null",
    "hero_product_link": "specific hero product name the CA could reference, or null — do NOT invent if no extracted_product",
    "recommended_product_entry": "specific entry-tier product name for this trend, or null",
    "recommended_product_core": "specific core-tier product name for this trend, or null",
    "recommended_product_stretch": "specific stretch-tier product name for this trend, or null",
    "composite_score": number,
    "reasoning": "4-6 sentences. Must: (1) name the matched archetype and explain specifically why they would respond; (2) name a specific hero product if ca_conversational_utility >= 7; (3) name the pillar confirmed or extended; (4) cite at least one snippet or metric as evidence.",
    "confidence": "high" or "medium" or "low",
    "evidence_references": ["direct quote or metric from the trend object"],
    "disqualifying_reason": null or "exact dimension that failed and why"
  }}
]"""
