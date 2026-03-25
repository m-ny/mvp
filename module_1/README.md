# XHS Trend Object Builder (Week 9 Module 1)

This repo is scoped to **one agent** and **one decision** for Week 9.

---

## Core (Non-Negotiable) Deliverable

A 5-minute live demo of a working agent loop:

`Prompt -> Retrieve -> Decide -> Output -> Trace/Log -> Human Feedback captured`

---

## Part A - Define Your Agent

### A1) Agent Name

`XHS Trend Object Builder`

### A2) ONE Decision (scope lock)

From a set of XHS posts for a brand/category and time window, produce distinct trend objects (cluster + label) and attach evidence and basic metrics per trend.

### A3) Output Type

`Type B: Reviewable output`

### A4) Success Metrics + Pass Thresholds

| Metric | Pass threshold type |
| --- | --- |
| Trend distinctness (duplicates/noise) | `Boolean + ratio threshold`: `duplicates/noise = no` in >=2 of 3 reviewer feedback entries |
| Evidence adequacy per trend object | `Coverage threshold`: 100% of trend objects include evidence IDs/snippets and metrics (`post_count`, engagement) |
| Reviewer quality score | `Average score threshold`: mean quality score >= 4.0 / 5 across >=3 feedback entries |
| End-to-end loop reliability | `Binary completion threshold`: at least 1 real run outputs trend objects + run log + feedback file |

---

## Part B - Agent Loop Build

Detailed prompt documentation:

- `README_PROMPT.md`

### B1) Prompt (exact text)

Given XHS posts for a single brand/category and time window, identify distinct trends by clustering semantically similar posts. For each trend, generate: 1) a short trend label, 2) a one-sentence description, 3) the evidence posts used, 4) basic metrics including post count and total engagement, 5) a confidence level. Do not invent evidence. If evidence is weak or overlapping, mark confidence low and explain ambiguity.

### B2) Retrieval (mandatory)

- **Retrieved objects (1-2):**
  - `data/xhs_posts.json`
  - `data/run_config.json`
- **Source:** local files
- **Records:** >= 5 (this repo has more than 5)

### B3) Decision Logic (mandatory)

Current implementation: **rules-first with optional LLM label/summary refinement**

Decision criteria:

1. Semantic similarity (token overlap / Jaccard) between posts.
2. Distinctness between clusters (avoid duplicate trend labels).
3. Evidence sufficiency (prefer >=2 posts per trend unless ambiguity).

Evidence requirements:

1. Include supporting `post_ids` and title snippets in each trend.
2. Include metrics from retrieved posts only (`post_count`, engagement).

Failure mode:

- If evidence is weak or mixed, output fewer trends and lower confidence.

### B4) Output (Type B reviewable object)

Each `trend_object` includes this structured schema:

- `trend_id`
- `label`
- `category`
- `ai_reasoning`
- `evidence`
- `metrics`
- `timestamp`
- `summary`
- `confidence`
- `labeling_source` (`llm` or `heuristic`)

Formal schema file:

- `outputs/trend_object_schema.json`

What reviewer judges:

- Are grouped posts truly about the same trend?
- Is each trend label clear and non-duplicative?
- Is evidence sufficient and correctly attached?

### B5) Trace + Logging (mandatory)

`outputs/runs/run_XXXX_run_log.json` includes:

- prompt
- retrieved sources
- decision output file
- evidence used
- confidence
- next step suggestion

### B6) Human Feedback (mandatory)

`outputs/runs/run_XXXX_feedback.json` includes >=3 reviewer entries with:

- quality (1-5)
- missing info
- duplicates/noise

---

## Part C - 5-Minute Demo Script (strict order)

Use this exact order and script:

1. **State the decision** - "Our agent takes XHS posts for a brand/category and time window and produces distinct trend objects with evidence and metrics."
2. **Show prompt** - "Here is the exact prompt the agent uses to create trend objects."
3. **Run agent live** - "We load the post dataset and config file, then run the trend object builder."
4. **Show output + evidence** - "These are the trend objects, each with a label, evidence posts, and engagement metrics."
5. **Show trace log** - "Here is the saved run log showing prompt, retrieved sources, evidence used, confidence, and next step."
6. **Show feedback** - "Here are 3 reviewer entries showing quality score, missing information, and whether there was duplicate noise."
7. **Show metric + next test** - "This week we passed end-to-end generation and reviewability; next week we’ll test better clustering and stronger distinctness."

---

## MVP Outcome Statement

If our MVP works, trend signals from Xiaohongshu become faster to validate and easier for downstream teams to reuse, because the system converts raw API/XHS inputs into strict, evidence-backed Trend Objects instead of fragmented content or slide-style summaries.

## Primary MVP Feature

The primary MVP feature is a **Trend Object Builder** that converts raw Xiaohongshu signals into a strict reusable Trend Object schema (label/category/evidence/metrics/timestamp/summary/confidence). Even alone, this is valuable because it reduces manual checking, improves trust, and standardizes downstream handoff.

---

## Model + API Key Setup (your question)

### Recommended model

- Default: **no model required** (rules-only, cheapest, stable demo).
- Optional AI refinement: `gpt-4.1-mini` for label/summary/confidence.
- If you want even cheaper/faster, use a smaller model in `run_config.json`.

### Where to put API key

Put your key in `.env` (project root):

```env
OPENAI_API_KEY=your_real_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Do **not** hardcode keys in Python files.

Enable optional LLM usage in `data/run_config.json`:

```json
"llm": {
  "enabled": true,
  "model": "gpt-4.1-mini"
}
```

If `llm.enabled` is `false` or no key is found, script falls back to rules-only mode automatically.

---

## Local Run

### 1) Install dependency (only if using LLM mode)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install openai
```

### 2) Run

```bash
python3 xhs_trend_builder.py
```

Run with explicit live LLM test:

```bash
python3 xhs_trend_builder.py --llm-test
```

Optional custom args:

```bash
python3 xhs_trend_builder.py --posts data/xhs_posts.json --config data/run_config.json --output-dir outputs
```

---

## Project Structure

- `xhs_trend_builder.py` - local runnable agent loop
- `data/xhs_posts.json` - input dataset
- `data/run_config.json` - retrieval scope + prompt + llm settings
- `outputs/trend_object_schema.json` - output schema definition
- `outputs/runs/run_XXXX_trend_objects.json` - reviewable trend object output (real run)
- `outputs/runs/run_XXXX_run_log.json` - trace/log from real run
- `outputs/runs/run_XXXX_feedback.json` - reviewer feedback entries
- `outputs/runs/run_XXXX_trace.log` - detailed CLI trace log
- `outputs/*.json` and `outputs/run_trace.log` - latest run convenience copies
- `.env.example` - API key template
- `.gitignore` - ignores `.env`
