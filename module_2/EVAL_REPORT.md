# Module 2 — Evaluation Report

**Run ID:** m2_20260421_131122  
**Generated at:** 2026-04-21T13:11:22.634249+00:00  
**Brand:** Tiffany & Co.

---

## Batch Composition

| Source | Count |
|--------|-------|
| Real XHS (luxury_jewelry) | 378 |
| Synthetic (luxury_jewelry) | 0 |
| Beauty runs skipped | 0 |
| **Total input to filter** | **378** |

---

## Filter Results

- Pre-filter rejected: **117**
- Passed to LLM: **42**
- Shortlisted: **11**
- Noise reduction rate: **97.1%**

---

## Quality Checks

### 1. Off-Brand Rate
- Off-brand count: 22 (5.8% of input)
  - Taboo keyword rejections: 0
  - LLM brand_fit < 5: 22

### 2. Explanation Specificity (LLM confidence breakdown)
- High: 11 (26.2%)
- Medium: 17 (40.5%)
- Low: 14 (33.3%)

### 3. Noise Reduction
- 97.1% of input trends were filtered before reaching the shortlist.

### 4. Signal Detection & New Dimensions
- **Extracted product**: 8 of 11 shortlisted trends had a real XHS product mention (hero_product set).
- **Celebrity signal**: 6 of 42 evaluated trends (14.0%)
- **Occasion signal**: 3 of 42 evaluated trends (7.0%)
- **Competitor signal**: 2 of 42 evaluated trends (4.7%)
- **Trend Velocity**: computed from engagement_recency_pct (7-day recency) or save-ratio proxy when no dates available.
- **Evidence Credibility**: computed from run_count × confidence weight.

---

## Shortlist Summary

Shortlisted **11** trends (real: 11, synthetic: 0):

| # | Trend | CWC Score | Raw Score | Extracted Product | Brand Depth | CA Touch | Velocity |
|---|-------|-----------|-----------|------------------|------------|---------|---------|
| 1 | **[run_0001_t09]** Bridal Diaries and Engagement Ring Purchase Stories | 8.15 | 8.15 | Tiffany Setting | 9 | 10 | 10.0 |
| 2 | **[run_0001_t15]** Wedding Band and Matching Ring Discussions | 8.15 | 8.15 | Tiffany Setting | 9 | 9 | 10.0 |
| 3 | **[run_0001_t01]** HardWear Collection Styling and Layering | 8.10 | 8.10 | HardWear | 9 | 9 | 10.0 |
| 4 | **[run_0001_t02]** Tiffany Blue Aesthetic and Color Appreciation | 8.10 | 8.10 | 蒂芙尼 | 9 | 9 | 10.0 |
| 5 | **[run_0001_t05]** Milestone Gifting and Unboxing Experiences | 8.00 | 8.00 | — | 8 | 8 | 10.0 |
| 6 | **[run_0001_t03]** Six-Prong Setting and Classic Engagement Ring Discussions | 7.90 | 7.90 | 蒂芙尼 | 9 | 8 | 10.0 |
| 7 | **[run_0001_t13]** Celebrity and Influencer Endorsements and Event Appearances | 7.90 | 7.90 | 蒂芙尼 | 9 | 8 | 10.0 |
| 8 | **[run_0001_t11]** Smile and Heart Tag Necklace Popularity | 7.90 | 7.90 | — | 9 | 9 | 10.0 |
| 9 | **[run_0001_t16]** Mini and Micro Jewelry Trends | 7.85 | 7.85 | 蒂芙尼 | 8 | 9 | 10.0 |
| 10 | **[run_0001_t07]** Double T and T1 Bracelet Layering and Popularity | 7.75 | 7.75 | T wire | 8 | 9 | 10.0 |
| 11 | **[run_0001_t23]** Smile Necklace Entry-Level Purchase Guides | 7.50 | 7.50 | — | 9 | 8 | 10.0 |

---

## Failure Cases (5 Lowest Scoring)

- **[run_0018_t07]** Relaxed and Effortless Menswear Styling — score: 1.99
  - Reason: client_touchpoint_specificity < 4 — no link to Tiffany products.
  - brand_engagement_depth: 3 | client_touchpoint_specificity: 2 | intelligence_value: 2
- **[run_0040_t05]** French Minimalism and Understated Elegance Aesthetic — score: 1.99
  - Reason: client_touchpoint_specificity < 4 — no link to Tiffany products.
  - brand_engagement_depth: 3 | client_touchpoint_specificity: 2 | intelligence_value: 2
- **[run_0018_t02]** Quiet Luxury Minimalism — score: 2.03
  - Reason: brand_engagement_depth too low; general jewelry context lacks Tiffany specificity.
  - brand_engagement_depth: 2 | client_touchpoint_specificity: 1 | intelligence_value: 3
- **[run_0018_t06]** Celebrity-Influenced Brand Enthusiasm — score: 2.06
  - Reason: client_touchpoint_specificity failed — no recognizable bridge to a Tiffany conversation with clients.
  - brand_engagement_depth: 3 | client_touchpoint_specificity: 1 | intelligence_value: 3
- **[run_0038_t23]** Mixed Trend Signals — score: 2.06
  - Reason: client_touchpoint_specificity < 4 — no link to Tiffany products.
  - brand_engagement_depth: 3 | client_touchpoint_specificity: 2 | intelligence_value: 2

---

## Known Limitations

1. Runs 0001–0008 are beauty category and excluded — not relevant for luxury jewelry brand filtering.
2. Runs 0009–0013 contain identical underlying XHS data (same 3 posts scraped across 5 runs).
3. Synthetic trends are clearly marked `data_type: synthetic` and should not be presented as real XHS signal.
4. No image URLs captured — scraping ran with `--no-detail` flag.
