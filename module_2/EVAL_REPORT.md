# Module 2 — Evaluation Report

**Run ID:** m2_20260329_152623  
**Generated at:** 2026-03-29T15:26:23.983657+00:00  
**Brand:** Celine

---

## Batch Composition

| Source | Count |
|--------|-------|
| Real XHS (luxury_fashion) | 15 |
| Synthetic (luxury_fashion) | 25 |
| Beauty runs skipped | 40 |
| **Total input to filter** | **40** |

---

## Filter Results

- Pre-filter rejected: **1**
- Passed to LLM: **39**
- Shortlisted: **15**
- Noise reduction rate: **62.5%**

---

## Quality Checks

### 1. Off-Brand Rate
- Off-brand count: 1 (2.5% of input)
  - Taboo keyword rejections: 1
  - LLM brand_fit < 5: 0

### 2. Explanation Specificity (LLM confidence breakdown)
- High: 22 (56.4%)
- Medium: 17 (43.6%)
- Low: 0 (0.0%)

### 3. Noise Reduction
- 62.5% of input trends were filtered before reaching the shortlist.

---

## Shortlist Summary

Shortlisted **15** trends (real: 4, synthetic: 11):

- **[synthetic_t03]** Triomphe Hardware Investment — score: 9.30
- **[run_0009_t01]** Mixed Beauty Trend Signals — score: 9.25
- **[run_0010_t01]** Minimalist Tailoring & Structure — score: 9.25
- **[synthetic_t22]** Season-less Wardrobe Building — score: 9.20
- **[synthetic_t02]** Architectural Silhouette Dressing — score: 9.10
- **[synthetic_t21]** Parisian Academic Intellectual Style — score: 9.10
- **[run_0013_t01]** Celine's Quiet Luxury Trend — score: 9.00
- **[synthetic_t23]** Satin and Silk Luxury Surface Dressing — score: 9.00
- **[synthetic_t24]** Clean Minimalist Aesthetic as Identity — score: 9.00
- **[synthetic_t06]** French Intellectual Editorial Aesthetic — score: 8.70
- **[synthetic_t10]** Oversized Structured Blazer Power Dressing — score: 8.70
- **[synthetic_t15]** Understated Leather Goods Connoisseurship — score: 8.65
- **[run_0011_t01]** Celine Minimalism and Quiet Luxury — score: 8.60
- **[synthetic_t08]** Cashmere Quiet Luxury Layering — score: 8.60
- **[synthetic_t14]** Capsule Wardrobe Investment Mentality — score: 8.55

---

## Failure Cases (5 Lowest Scoring)

- **[run_0012_t01]** Celine's Minimalist Aesthetic — score: 4.55
  - Reason: freshness and materiality – insufficient recent traction
- **[run_0010_t03]** Minimalist Tailoring & Structure — score: 5.10
  - Reason: freshness and materiality – not enough traction and low engagement
- **[run_0010_t02]** Luxury Handbag & Leather Goods — score: 5.25
  - Reason: materiality: insufficient engagement and interest with only 3 posts
- **[run_0009_t03]** Mixed Beauty Trend Signals — score: 5.40
  - Reason: materiality: insufficient engagement and post count
- **[run_0012_t02]** Celine Workplace Fashion — score: 5.55
  - Reason: freshness - low engagement and limited recency of posts

---

## Known Limitations

1. Runs 0001–0008 are beauty category and excluded — not relevant for Celine.
2. Runs 0009–0013 contain identical underlying XHS data (same 3 posts scraped across 5 runs).
3. Synthetic trends are clearly marked `data_type: synthetic` and should not be presented as real XHS signal.
4. No image URLs captured — scraping ran with `--no-detail` flag.

---

## Fix for Next Week

Based on the 5 failure cases above, the primary issue is insufficient post_count and low engagement in real XHS runs. The planned fix is to request Module 1 to scrape more Celine luxury_fashion posts with higher engagement, and to raise the minimum post_count threshold from 2 to 5 for real XHS trends to reduce low-signal noise passing through to LLM evaluation.
