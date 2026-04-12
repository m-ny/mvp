# Module 2 — Evaluation Report

**Run ID:** m2_20260412_062446  
**Generated at:** 2026-04-12T06:24:46.969004+00:00  
**Brand:** Celine

---

## Batch Composition

| Source | Count |
|--------|-------|
| Real XHS (luxury_fashion) | 69 |
| Synthetic (luxury_fashion) | 0 |
| Beauty runs skipped | 40 |
| **Total input to filter** | **69** |

---

## Filter Results

- Pre-filter rejected: **30**
- Passed to LLM: **36**
- Shortlisted: **14**
- Noise reduction rate: **79.7%**

---

## Quality Checks

### 1. Off-Brand Rate
- Off-brand count: 0 (0.0% of input)
  - Taboo keyword rejections: 0
  - LLM brand_fit < 5: 0

### 2. Explanation Specificity (LLM confidence breakdown)
- High: 23 (63.9%)
- Medium: 12 (33.3%)
- Low: 1 (2.8%)

### 3. Noise Reduction
- 79.7% of input trends were filtered before reaching the shortlist.

### 4. New Dimensions (Week 11)
- **CA Conversational Utility**: % of shortlisted trends with a named hero product link — 13 of 36 evaluated trends had a specific product anchor.
- **Client Archetype Coverage**: archetypes matched across shortlist — 摇滚缪斯 Yáogǔn Miùsī, 智识派 Zhishì Pài, 独立新贵 Dúlì Xīnguì
- **Trend Velocity**: scores computed from engagement_recency_pct (7-day recency window).
- **Cross-Run Persistence**: scores computed from run_count (deduplication merged trends retain count).

---

## Shortlist Summary

Shortlisted **14** trends (real: 14, synthetic: 0):

| # | Trend | Score | Archetype | Hero Product | Pillar | CA Utility | Velocity |
|---|-------|-------|-----------|-------------|--------|-----------|---------|
| 1 | **[run_0013_t01]** Celine's Quiet Luxury Trend | 8.04 | 智识派 Zhishì Pài | Celine Triomphe canvas shoulder bag | Rock Intellectualism | 8 | 6.6 |
| 2 | **[run_0011_t02]** Celine Workwear Essentials | 7.90 | 独立新贵 Dúlì Xīnguì | Celine Classique 16 bag | — | 9 | 10.0 |
| 3 | **[run_0012_t01]** Celine's Minimalist Aesthetic | 7.89 | 智识派 Zhishì Pài | Celine Triomphe canvas shoulder bag | Architectural Restraint | 8 | 6.6 |
| 4 | **[run_0011_t01]** Celine Minimalism and Quiet Luxury | 7.79 | 智识派 Zhishì Pài | Celine Essential slim-cut tuxedo blazer | Architectural Restraint | 8 | 6.6 |
| 5 | **[run_0017_t02]** Celine Blue Label Minimalist Aesthetics | 7.75 | 摇滚缪斯 Yáogǔn Miùsī | Celine Classique 16 bag | Youth Without Apology | 9 | 5.0 |
| 6 | **[run_0023_t02]** Celebrity Outfit Decoding and Influence Content | 7.55 | 摇滚缪斯 Yáogǔn Miùsī | Celine Essential slim-cut tuxedo blazer | Rock Intellectualism | 8 | 5.0 |
| 7 | **[run_0014_t01]** Mixed Trend Signals | 7.45 | 摇滚缪斯 Yáogǔn Miùsī | Celine oversized leather biker jacket | Youth Without Apology | 8 | 5.0 |
| 8 | **[run_0019_t06]** Celebrity Celine Show Attendance and Styling Highlights | 7.40 | 摇滚缪斯 Yáogǔn Miùsī | Celine oversized leather biker jacket | Youth Without Apology | 9 | 5.0 |
| 9 | **[run_0018_t02]** Quiet Luxury Minimalism | 7.35 | 独立新贵 Dúlì Xīnguì | Celine essential slim-cut tuxedo blazer | Architectural Restraint | 8 | 5.0 |
| 10 | **[run_0019_t02]** Celine Blue Label Design Detail Appreciation | 7.35 | 独立新贵 Dúlì Xīnguì | Celine essential slim-cut tuxedo blazer | Architectural Restraint | 8 | 5.0 |
| 11 | **[run_0018_t06]** Celebrity-Influenced Brand Enthusiasm | 7.30 | 摇滚缪斯 Yáogǔn Miùsī | Celine oversized leather biker jacket | Youth Without Apology | 9 | 5.0 |
| 12 | **[run_0014_t02]** Luxury Handbag & Leather Goods | 7.25 | 智识派 Zhishì Pài | Celine Teen Triomphe bag in natural calfskin | Architectural Restraint | 9 | 5.0 |
| 13 | **[run_0017_t06]** 王安宇Celine时尚秀场 | 7.15 | 摇滚缪斯 Yáogǔn Miùsī | Celine oversized leather biker jacket | Youth Without Apology | 8 | 5.0 |
| 14 | **[run_0021_t01]** Celine Blue Label Design Appreciation | 6.75 | 智识派 Zhishì Pài | — | Architectural Restraint | 6 | 5.0 |

---

## Failure Cases (5 Lowest Scoring)

- **[run_0021_t04]** CELINE 26 Summer Menswear Soft Relaxed Jacket Showcase — score: 4.60
  - Reason: client_persona_match failed due to a lack of alignment with the core clientele profile focused on women's luxury apparel.
  - Target archetype: no archetype matched | client_persona_match: 3 | ca_conversational_utility: 4 | novelty: 5
- **[run_0018_t07]** Relaxed and Effortless Menswear Styling — score: 4.60
  - Reason: novelty — lacks significant new insights regarding engagement
  - Target archetype: no archetype matched | client_persona_match: 5 | ca_conversational_utility: 4 | novelty: 3
- **[run_0012_t03]** Celine Tailoring and Fabric Insights — score: 4.65
  - Reason: client_persona_match failed — trend does not resonate with any archetype.
  - Target archetype: no archetype matched | client_persona_match: 4 | ca_conversational_utility: 5 | novelty: 6
- **[run_0018_t03]** Seasonal Luxury Accessory Refresh — score: 4.65
  - Reason: client_persona_match — does not align with archetype values of timelessness and quiet luxury
  - Target archetype: no archetype matched | client_persona_match: 4 | ca_conversational_utility: 4 | novelty: 3
- **[run_0017_t07]** CELINE 26 Summer Men's Relaxed Jackets — score: 4.80
  - Reason: All dimensions scores below threshold, especially low ca_conversational_utility due to gender misalignment.
  - Target archetype: no archetype matched | client_persona_match: 5 | ca_conversational_utility: 4 | novelty: 3

---

## Known Limitations

1. Runs 0001–0008 are beauty category and excluded — not relevant for Celine.
2. Runs 0009–0013 contain identical underlying XHS data (same 3 posts scraped across 5 runs).
3. Synthetic trends are clearly marked `data_type: synthetic` and should not be presented as real XHS signal.
4. No image URLs captured — scraping ran with `--no-detail` flag.
