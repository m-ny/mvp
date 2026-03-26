-- Module 2: Trend Relevance & Materiality Filter
-- Stores the LLM-evaluated shortlist of top trends passed to Module 3.

CREATE TABLE IF NOT EXISTS module2_trend_shortlist (
    id              BIGSERIAL PRIMARY KEY,
    run_id          TEXT NOT NULL,
    module1_run_id  TEXT,
    brand           TEXT,
    trend_id        TEXT,
    rank            INTEGER,
    label           TEXT,
    category        TEXT,
    composite_score NUMERIC(5,2),
    score_freshness     NUMERIC(4,1),
    score_brand_fit     NUMERIC(4,1),
    score_category_fit  NUMERIC(4,1),
    score_materiality   NUMERIC(4,1),
    score_actionability NUMERIC(4,1),
    confidence          TEXT,
    why_selected        TEXT,
    evidence_references JSONB DEFAULT '[]',
    metric_signal       JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_m2_shortlist_run ON module2_trend_shortlist(run_id);
CREATE INDEX IF NOT EXISTS idx_m2_shortlist_trend ON module2_trend_shortlist(trend_id);


CREATE TABLE IF NOT EXISTS module2_run_logs (
    id                   BIGSERIAL PRIMARY KEY,
    run_id               TEXT UNIQUE NOT NULL,
    module1_run_id       TEXT,
    total_input          INTEGER,
    prefilter_rejected   INTEGER,
    passed_to_llm        INTEGER,
    shortlisted          INTEGER,
    noise_reduction_pct  NUMERIC(5,1),
    generated_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);
