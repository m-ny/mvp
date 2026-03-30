# Module 2 — Evaluation Report

**Run ID:** m2_20260330_043843  
**Generated at:** 2026-03-30T04:38:43.349649+00:00  
**Brand:** Celine

---

## Batch Composition

| Source | Count |
|--------|-------|
| Real XHS (luxury_fashion) | 100 |
| Synthetic (luxury_fashion) | 25 |
| Beauty runs skipped | 40 |
| **Total input to filter** | **125** |

---

## Filter Results

- Pre-filter rejected: **86**
- Passed to LLM: **39**
- Shortlisted: **15**
- Noise reduction rate: **88.0%**

---

## Quality Checks

### 1. Off-Brand Rate
- Off-brand count: 1 (0.8% of input)
  - Taboo keyword rejections: 1
  - LLM brand_fit < 5: 0

### 2. Explanation Specificity (LLM confidence breakdown)
- High: 21 (53.8%)
- Medium: 18 (46.2%)
- Low: 0 (0.0%)

### 3. Noise Reduction
- 88.0% of input trends were filtered before reaching the shortlist.

---

## Shortlist Summary

Shortlisted **15** trends (real: 5, synthetic: 10):

- **[synthetic_t02]** Architectural Silhouette Dressing — score: 9.35
- **[synthetic_t06]** French Intellectual Editorial Aesthetic — score: 9.35
- **[synthetic_t03]** Triomphe Hardware Investment — score: 9.25
- **[run_0013_t01]** Celine's Quiet Luxury Trend — score: 9.15
- **[run_0010_t01]** Minimalist Tailoring & Structure — score: 9.10
- **[synthetic_t04]** Monochromatic Precision Dressing — score: 9.05
- **[synthetic_t24]** Clean Minimalist Aesthetic as Identity — score: 8.85
- **[synthetic_t15]** Understated Leather Goods Connoisseurship — score: 8.65
- **[run_0011_t01]** Celine Minimalism and Quiet Luxury — score: 8.60
- **[run_0012_t01]** Celine's Minimalist Aesthetic — score: 8.60
- **[synthetic_t23]** Satin and Silk Luxury Surface Dressing — score: 8.60
- **[synthetic_t13]** Intellectual Feminine Dressing — score: 8.55
- **[synthetic_t10]** Oversized Structured Blazer Power Dressing — score: 8.40
- **[run_0009_t01]** Mixed Beauty Trend Signals — score: 8.25
- **[synthetic_t08]** Cashmere Quiet Luxury Layering — score: 8.20

---

## Failure Cases (5 Lowest Scoring)

- **[synthetic_t16]** Caramel and Cognac Color Story — score: 5.40
  - Reason: brand_fit - lacks alignment with Celine's rigorous simplicity
- **[run_0009_t03]** Mixed Beauty Trend Signals — score: 5.55
  - Reason: freshness - posts do not indicate growing interest
- **[run_0010_t02]** Luxury Handbag & Leather Goods — score: 5.55
  - Reason: materiality - low engagement metrics, insufficient signal in luxury context
- **[run_0012_t03]** Celine Tailoring and Fabric Insights — score: 5.55
  - Reason: freshness - low post recency and count
- **[run_0013_t03]** Celine Tailoring Insights — score: 5.55
  - Reason: freshness - low post recency and count

---

## Known Limitations

1. Runs 0001–0008 are beauty category and excluded — not relevant for Celine.
2. Runs 0009–0013 contain identical underlying XHS data (same 3 posts scraped across 5 runs).
3. Synthetic trends are clearly marked `data_type: synthetic` and should not be presented as real XHS signal.
4. No image URLs captured — scraping ran with `--no-detail` flag.
