# IO_CONTRACT.md — Module 2: Trend Relevance & Materiality Filter

**Version:** Week 11 (35 Supabase columns, 8 scoring dimensions, 3 archetypes, organic product extraction)

---

## Inputs

### Source files
| Source | Path | Notes |
|--------|------|-------|
| Real XHS trends | `module_1/outputs/runs/run_*_trend_objects.json` | Loaded via glob; beauty category skipped |
| Synthetic trends | `module_2/data/synthetic_trends.json` | Disabled in Week 11 (real XHS only) |
| Brand profile | `module_2/brand_profile_{slug}.json` | e.g. `brand_profile_celine.json` |

### Required fields per trend object
| Field | Type | Used by |
|-------|------|---------|
| `trend_id` | string | Namespaced at load time as `run_XXXX_tYY` |
| `label` | string | Pre-filter (taboo, menswear), LLM prompt |
| `category` | string | Must match `active_categories` in brand profile |
| `summary` | string | Pre-filter, LLM context |
| `evidence.snippets[]` | string[] | Min 2 required; brand signal check; LLM grounding |
| `evidence.posts[].date` | ISO 8601 | Freshness check (21-day cutoff); recency pct |

### Optional fields per trend object
| Field | Type | Fallback |
|-------|------|---------|
| `location` | string | Defaults to `"China"` |
| `metrics.post_count` | int | 0 if missing; 2–4 passes with `low_signal_warning` for luxury_fashion |
| `evidence.posts[].likes/comments/saves` | int | Used for `engagement_recency_pct` |

### Brand profile required structure
```json
{
  "brand_name": "string",
  "brand_name_cn": "string",
  "active_categories": ["luxury_fashion", ...],
  "brand_taboos": {"group": ["keyword", ...]},
  "client_archetypes": [{"name": "...", "age_range": "...", "lifestyle": "..."}],
  "hero_products": {"ready_to_wear": [...], "leather_goods": [...], "accessories": [...]},
  "aesthetic_pillars": [{"name": "...", "description": "..."}]
}
```

### Environment variables
| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | Yes | LLM evaluation via OpenRouter |
| `BRAND` | No | Brand slug; defaults to `"Louis Vuitton"` |
| `DEFAULT_MODEL` | No | Model ID; defaults to `"anthropic/claude-3-5-sonnet"` |
| `SUPABASE_PASSWORD` | No | DB write; agent completes locally if absent |

---

## Processing Pipeline

### Step A — Cross-run deduplication (scorer.py)
Jaccard word-token similarity on `label + summary`. Pairs ≥ 70% similar are merged.
Merged trends: combined snippets + posts, summed metrics, `data_type = "merged"`, `run_count` incremented.

### Step B — Engagement recency (scorer.py)
For each trend: % of total engagement (likes + comments + saves) from posts within last 7 days.
Stored as `engagement_recency_pct` on the trend object for use in Step 2 scoring.

### Step C — Pre-filter rules (scorer.py)
| Rule | Condition | Action |
|------|-----------|--------|
| 1 | `category` not in `active_categories` | Hard reject |
| 2 | `post_count < 2` | Hard reject; 2–4 passes with `low_signal_warning` (luxury_fashion only) |
| 3 | *(removed)* | — |
| 4 | Last post date confirmed > 21 days old | Hard reject; no dates → pass with `no_date_signal` |
| 5 | `len(snippets) < 2` | Hard reject |
| 6 | Label or summary contains brand taboo keyword | Hard reject |
| 7 | Label or summary contains menswear keyword (`men's`, `menswear`, `男装`, `男士`, `homme`) and `menswear` not in `active_categories` | Hard reject — `"menswear content — not in active categories for this brand"` |
| 8 | Fewer than 2 snippets contain brand name / hero product / pillar keyword (real trends only) | Hard reject — `"Insufficient brand signal"` |

### Step 1.5 — Organic product extraction (agent.py)
Scans all snippets + post titles for 13 known brand product names.
Counts occurrences; stores most-mentioned as `extracted_product` on trend object.
Used to ground `ca_conversational_utility` scoring and as preferred `hero_product` source.

### Step 2 — LLM evaluation (evaluator.py, prompts.py)
Batches of 5 trends sent to OpenRouter. LLM scores 6 dimensions (0–10 each):
`brand_fit`, `ca_conversational_utility`, `language_specificity`, `client_persona_match`, `novelty`, `category_fit`.

LLM also returns: `matched_archetype` (must use exact archetype name), `matched_pillar`, `hero_product_link`.

**If `extracted_product` is present on a trend:** LLM is instructed to reference it directly in `hero_product_link` and reasoning. If absent, LLM must not invent a product name.

Algorithmic dimensions added post-LLM (not scored by LLM):
- `trend_velocity` — from `engagement_recency_pct`: >70% → 8–10, 40–70% → 5–7, <40% → 1–4. If `no_date_signal`, set to neutral 5.0 and excluded from minimum threshold check.
- `cross_run_persistence` — from `run_count`: ≥3 → 10, 2 → 7, 1 → 5.

### Step 3 — Composite score & shortlist selection (evaluator.py)
**Composite formula:**

| Dimension | Weight |
|-----------|--------|
| `brand_fit` | 0.20 |
| `ca_conversational_utility` | 0.20 |
| `trend_velocity` | 0.15 |
| `language_specificity` | 0.15 |
| `client_persona_match` | 0.10 |
| `novelty` | 0.10 |
| `category_fit` | 0.05 |
| `cross_run_persistence` | 0.05 |

**Shortlist qualification:**
- `composite_score ≥ 6.5`
- All LLM dimensions ≥ 4 (except `ca_conversational_utility` minimum = 4, `cross_run_persistence` minimum = 3)
- `shortlist == true` from LLM judgment

---

## Client Archetypes

| Name | Age | Profile |
|------|-----|---------|
| 智识派 Zhishì Pài | 32–42 | Cultural capital, intellectual aspiration |
| 独立新贵 Dúlì Xīnguì | 26–34 | Self-made, independent luxury |
| 摇滚缪斯 Yáogǔn Miùsī | 22–30 | Rock aesthetic, anti-conventional luxury |

`client_persona_match` must name one of these exact strings in the `matched_archetype` field.

---

## Subcategory Inference

Applied in `supabase_writer.py` to every shortlisted trend using label + hero_product + why_selected:

| Subcategory | Signal keywords |
|-------------|----------------|
| `leather_goods` | bag, handbag, tote, clutch, purse, triomphe, 包, 手袋, 皮具 |
| `ready_to_wear` | blazer, jacket, trouser, coat, dress, shirt, skirt, 外套, 西装, 大衣 |
| `accessories` | sunglasses, belt, scarf, jewel, chain, bracelet, ring, 眼镜, 腰带 |
| `footwear` | boots, shoes, sneaker, heel, loafer, 靴, 鞋 |
| `general_aesthetic` | *(default if no signal matches)* |

---

## Outputs

### 1. Local shortlist backup
**Path:** `module_2/outputs/output_shortlist.json`

Key fields per shortlist item: `trend_id`, `label`, `category`, `location`, `data_type`, `composite_score`, `scores{}` (8 dims), `matched_archetype`, `matched_pillar`, `extracted_product`, `hero_product`, `hero_product_source`, `hero_product_link`, `confidence`, `why_selected`, `evidence_references[]`, `metric_signal{}`.

### 2. Module 3 handoff
**Path:** `module_3/trend_brief_agent/trend_shortlist.json`

Fields passed to Module 3: all shortlist fields above plus `trend_label`, `city`, `cluster_summary`, `post_count`, `engagement_rate`, `top_post_example`, `trending_hashtags`, `brand_relevance`, `week_on_week_growth`, `m2_composite_score`, `m2_confidence`, `m2_why_selected`, `extracted_product`, `hero_product`, `hero_product_source`.

### 3. Supabase tables
**Table:** `module2_trend_shortlist` (35 columns, one row per shortlisted trend)

| Column | Type | Source |
|--------|------|--------|
| `id` | BIGSERIAL PK | auto |
| `run_id` | TEXT | agent run ID |
| `module1_run_id` | TEXT | source run range |
| `brand` | TEXT | brand profile |
| `trend_id` | TEXT | namespaced ID |
| `rank` | INTEGER | shortlist rank |
| `label` | TEXT | trend name |
| `category` | TEXT | trend category |
| `composite_score` | NUMERIC(5,2) | weighted formula |
| `score_freshness` | NUMERIC(4,1) | legacy |
| `score_brand_fit` | NUMERIC(4,1) | LLM |
| `score_category_fit` | NUMERIC(4,1) | LLM |
| `score_materiality` | NUMERIC(4,1) | legacy |
| `score_actionability` | NUMERIC(4,1) | legacy |
| `confidence` | TEXT | LLM |
| `why_selected` | TEXT | LLM reasoning |
| `evidence_references` | JSONB | LLM citations |
| `metric_signal` | JSONB | Module 1 metrics |
| `created_at` | TIMESTAMPTZ | auto |
| `location` | TEXT | trend object |
| `data_type` | TEXT | real/synthetic/merged |
| `subcategory` | TEXT | inferred |
| `client_persona_match_name` | TEXT | matched archetype |
| `hero_product` | TEXT | resolved (extracted > llm) |
| `hero_product_source` | TEXT | extracted_from_posts / llm_suggested |
| `score_ca_conversational_utility` | NUMERIC(4,1) | LLM |
| `score_language_specificity` | NUMERIC(4,1) | LLM |
| `score_client_persona_match` | NUMERIC(4,1) | LLM |
| `score_novelty` | NUMERIC(4,1) | LLM |
| `score_trend_velocity` | NUMERIC(4,1) | algorithmic |
| `score_cross_run_persistence` | NUMERIC(4,1) | algorithmic |
| `engagement_recency_pct` | NUMERIC(5,1) | computed |
| `low_signal_warning` | BOOLEAN | pre-filter flag |
| `no_date_signal` | BOOLEAN | pre-filter flag |
| `disqualifying_reason` | TEXT | rejection cause |

**Table:** `module2_run_logs` (one row per agent run)
Fields: `run_id`, `module1_run_id`, `total_input`, `prefilter_rejected`, `passed_to_llm`, `shortlisted`, `noise_reduction_pct`, `generated_at`, `created_at`.

**Upsert strategy:** `ON CONFLICT (run_id, trend_id) DO UPDATE` — safe to re-run.
**Fallback:** `ON CONFLICT DO NOTHING` if unique constraint missing.
**Supabase is optional** — agent always completes and saves locally if DB is unreachable.
