# Module 2 — Evaluation Report

**Run ID:** m2_20260421_135210  
**Generated at:** 2026-04-21T13:52:10.279980+00:00  
**Brand:** Tiffany & Co.

---

## Batch Composition

| Source | Count |
|--------|-------|
| Real XHS (luxury_jewelry) | 451 |
| Synthetic (luxury_jewelry) | 0 |
| Beauty runs skipped | 0 |
| **Total input to filter** | **451** |

---

## Filter Results

- Pre-filter rejected: **134**
- Passed to LLM: **94**
- Shortlisted: **15**
- Noise reduction rate: **96.7%**

---

## Quality Checks

### 1. Off-Brand Rate
- Off-brand count: 22 (4.9% of input)
  - Taboo keyword rejections: 0
  - LLM brand_fit < 5: 22

### 2. Explanation Specificity (LLM confidence breakdown)
- High: 46 (48.9%)
- Medium: 41 (43.6%)
- Low: 7 (7.4%)

### 3. Noise Reduction
- 96.7% of input trends were filtered before reaching the shortlist.

### 4. Signal Detection & New Dimensions
- **Extracted product**: 14 of 15 shortlisted trends had a real XHS product mention (hero_product set).
- **Celebrity signal**: 9 of 94 evaluated trends (9.6%)
- **Occasion signal**: 8 of 94 evaluated trends (8.5%)
- **Competitor signal**: 3 of 94 evaluated trends (3.2%)
- **Trend Velocity**: computed from engagement_recency_pct (7-day recency) or save-ratio proxy when no dates available.
- **Evidence Credibility**: computed from run_count × confidence weight.

---

## Shortlist Summary

Shortlisted **15** trends (real: 15, synthetic: 0):

| # | Trend | CWC Score | Raw Score | Extracted Product | Brand Depth | CA Touch | Velocity |
|---|-------|-----------|-----------|------------------|------------|---------|---------|
| 1 | **[run_0003_t03]** Unboxing of High-Price or Multiple-Stone Diamond Rings | 8.90 | 8.90 | HardWear | 9 | 10 | 10.0 |
| 2 | **[run_0007_t02]** Six-Prong Engagement Ring Popularity and Styling | 8.70 | 8.70 | 蒂芙尼 | 10 | 10 | 10.0 |
| 3 | **[run_0002_t04]** Blue Box Unboxing and Milestone Gift Sharing | 8.55 | 8.55 | 蒂芙尼 | 9 | 10 | 10.0 |
| 4 | **[run_0003_t02]** Everyday Minimalist Jewelry Enthusiasm | 8.55 | 8.55 | Tiffany Setting | 9 | 10 | 10.0 |
| 5 | **[run_0003_t01]** Social Media Influencer Boost to Jewelry Popularity | 8.50 | 8.50 | HardWear | 8 | 9 | 10.0 |
| 6 | **[run_0002_t10]** Classic Collection Retrospective and Iconic Piece Overviews | 8.40 | 8.40 | 蒂芙尼 | 10 | 10 | 10.0 |
| 7 | **[run_0007_t03]** Bridal and Wedding Ring Purchase Diaries | 8.40 | 8.40 | Tiffany Setting | 10 | 9 | 10.0 |
| 8 | **[run_0007_t01]** Tiffany Blue Color Aesthetic and Mood Posts | 8.25 | 8.25 | 蒂芙尼 | 10 | 9 | 10.0 |
| 9 | **[run_0001_t07]** Double T and T1 Bracelet Layering and Popularity | 8.20 | 8.20 | T wire | 9 | 9 | 10.0 |
| 10 | **[run_0001_t05]** Milestone Gifting and Unboxing Experiences | 8.15 | 8.15 | — | 9 | 8 | 10.0 |
| 11 | **[run_0001_t13]** Celebrity and Influencer Endorsements and Event Appearances | 8.05 | 8.05 | 蒂芙尼 | 9 | 9 | 10.0 |
| 12 | **[run_0001_t01]** HardWear Collection Styling and Layering | 7.90 | 7.90 | HardWear | 10 | 9 | 10.0 |
| 13 | **[run_0003_t05]** Long-Term Practical Jewelry Investment Sharing | 7.85 | 7.85 | 蒂芙尼 | 9 | 8 | 10.0 |
| 14 | **[run_0001_t09]** Bridal Diaries and Engagement Ring Purchase Stories | 7.80 | 7.80 | Tiffany Setting | 9 | 8 | 10.0 |
| 15 | **[run_0003_t12]** Classic Collection Aesthetic Overview and Compilation Posts | 7.75 | 7.75 | 蒂芙尼 | 9 | 8 | 10.0 |

---

## Failure Cases (5 Lowest Scoring)

- **[run_0040_t08]** Lists and Curated Recommendations for Seasonal Wardrobe Building — score: 2.78
  - Reason: brand_engagement_depth failed — no meaningful engagement with Tiffany products.
  - brand_engagement_depth: 3 | client_touchpoint_specificity: 4 | intelligence_value: 3
- **[run_0009_t01]** Mixed Beauty Trend Signals — score: 2.83
  - Reason: brand_engagement_depth and client_touchpoint_specificity too low
  - brand_engagement_depth: 3 | client_touchpoint_specificity: 3 | intelligence_value: 3
- **[run_0009_t02]** Scenario-Based Skincare Routines — score: 2.85
  - Reason: brand_engagement_depth: too generalized and not brand-specific
  - brand_engagement_depth: 2 | client_touchpoint_specificity: 3 | intelligence_value: 2
- **[run_0040_t01]** Celebrity Outfit Decoding Content — score: 3.20
  - Reason: brand_engagement_depth below 4 due to absence of Tiffany-specific references.
  - brand_engagement_depth: 3 | client_touchpoint_specificity: 2 | intelligence_value: 2
- **[run_0040_t02]** Seasonal Handbag Styling and Unboxing — score: 3.25
  - Reason: brand_engagement_depth below 4 due to lack of product-specific content from Tiffany & Co.
  - brand_engagement_depth: 3 | client_touchpoint_specificity: 2 | intelligence_value: 2

---

## Known Limitations

1. Runs 0001–0008 are beauty category and excluded — not relevant for luxury jewelry brand filtering.
2. Runs 0009–0013 contain identical underlying XHS data (same 3 posts scraped across 5 runs).
3. Synthetic trends are clearly marked `data_type: synthetic` and should not be presented as real XHS signal.
4. No image URLs captured — scraping ran with `--no-detail` flag.
