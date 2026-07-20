# Technical Documentation — Nalanda Investment Research Terminal (v1.0)

Last updated: 2026-07-18

This document describes the current implementation (code, architecture, data flow, integrations, and operational notes). It is intended for engineers and maintainers.

--------------------------------------------------------------------------------
1. Project overview
--------------------------------------------------------------------------------
- Purpose: an AI-assisted Investment Research Workspace that performs structured fundamental analysis (Nalanda Six Gates), valuation heuristics, generates an AI investment memo, and stores research records in a local Research Journal. The system is a Decision Support Terminal — not an automated trading system.
- Primary workflows:
  - On-demand "Analyze Company" (FMP primary, Yahoo fallback)
  - Build CompanyFinancialModel → run scoring (evaluate_overall) → produce AI memo and Investment Committee output
  - Optional Save to Research Journal (persist analysis + memo + evidence)

--------------------------------------------------------------------------------
2. Folder structure
--------------------------------------------------------------------------------
Top-level:
```
app/                         # Streamlit frontend (presentation only)
backend/                     # Business logic, connectors, scoring, DB helpers
  connectors/                # FMP connector (fmp.py)
  scoring/                   # Scoring engine modules and config loader
  services.py                # Orchestration: normalization, analyze, save, load
  db.py                      # SQLite engine + init_db(schema)
  schema.sql                 # DB schema
  cache.py                   # simple file cache
  mock_data.py               # mock sample data used in UI
config/
  scoring_rules.yaml         # Scoring weights/thresholds and rating map
docs/                        # Documentation (this file + others)
agents/                      # AI agent templates (prompts, wrappers)
data/                        # runtime cache and sqlite DB (gitignored)
requirements.txt
runtime.txt
VERSION
CHANGELOG.md
RELEASE_NOTES.md
```

--------------------------------------------------------------------------------
3. Technology stack
--------------------------------------------------------------------------------
- Language: Python 3.11 (runtime.txt)
- Web UI: Streamlit (>=1.22,<2.0)
- Data: Financial Modeling Prep (FMP) primary; yfinance (Yahoo) fallback
- DB: SQLite via SQLAlchemy (local storage for Research Journal and reports)
- AI: OpenAI-compatible wrapper placeholder (openai package) — currently deterministic memo generator
- Packaging: requirements.txt for dependencies

--------------------------------------------------------------------------------
4. Current architecture
--------------------------------------------------------------------------------
- Presentation layer: `app/streamlit_app.py` — renders pages, captures user actions, and calls backend services.
- Orchestration layer: `backend/services.py` — normalizes tickers, orchestrates data fetch (FMP → Yahoo), constructs `CompanyFinancialModel`, calls scoring (`evaluate_overall`), generates AI memo, and persists analysis on save.
- Connectors: `backend/connectors/fmp.py` — implements FMP endpoints and caches JSON responses via `backend/cache.py`.
- Scoring: `backend/scoring/*` — modular gate evaluators (profitability.py, management.py, moat.py, debt.py, cashflow.py, growth.py). `overall.py` aggregates weighted scores and computes pass/fail gates.
- Persistence: `backend/db.py` uses SQLAlchemy to open SQLite at `data/nalanda.db`. Schema defined in `backend/schema.sql`.

--------------------------------------------------------------------------------
5. Data flow
--------------------------------------------------------------------------------
User action: Analyze Company (ticker) → Streamlit sends ticker to `services.analyze_company()`.
1. `normalize_ticker()` applies rules (numeric → `.HK`, preserve suffix if present).
2. `fetch_company_financials()` attempts FMP connector (profile, income, balance, cashflow, ratios, key metrics).
3. If FMP fails, fallback to Yahoo (`yfinance.Ticker`) to fetch available tables.
4. Build `CompanyFinancialModel` (dataclass in backend/models.py) with DataFrames and raw JSON.
5. Call `evaluate_overall(model)`:
   - Each module .evaluate(model) returns evidence, 0–100 score, and summary.
   - overall aggregates weighted average, computes gates passed, confidence.
6. `services.generate_investment_summary()` produces AI memo (rule-based).
7. Return results to Streamlit for rendering.
8. If user clicks "Save", `services.save_analysis()` persists quality_scores rows, ai_reports, and research_journal entry.

--------------------------------------------------------------------------------
6. API integrations
--------------------------------------------------------------------------------
- Financial Modeling Prep (FMP)
  - Connector: `backend/connectors/fmp.py`
  - Endpoints used: profile, income-statement, balance-sheet-statement, cash-flow-statement, ratios, key-metrics
  - API key: `FMP_API_KEY` environment variable (dotenv loaded if available; not required for startup)
  - Caching: connector uses `backend/cache.py` file-based TTL cache to minimize calls.
- Yahoo Finance (fallback)
  - Connector: via `yfinance.Ticker` in `services.analyze_company()` fallback path
  - Used when FMP returns errors or missing data

--------------------------------------------------------------------------------
7. Database schema
--------------------------------------------------------------------------------
File: `backend/schema.sql` (applied via `backend/db.py::init_db()`)
Key tables:
- companies (id, ticker, exchange, name, last_updated)
- financial_metrics (company_id, source, metric_key, metric_value, as_of_date, raw_json)
- quality_scores (company_id, dimension, score, explanation, evidence_ref, evaluated_at)
- insider_transactions (company_id, date, insider_name, transaction_type, shares, value, source, raw_json)
- moat_analysis (company_id, moat_score, evidence, evaluated_at)
- ai_reports (company_id, report_type, content, created_at)
- research_journal (company_id, analysis_date, quality_score, valuation_json, recommendation, ai_memo, notes, review_date)

Evidence is stored as JSON strings in `quality_scores.evidence_ref`.

--------------------------------------------------------------------------------
8. Scoring engine design
--------------------------------------------------------------------------------
- Config-driven: `config/scoring_rules.yaml` contains `modules` with metric definitions, `weight`, `pass_threshold`, and `rating_stars`.
- Each gate module implements `evaluate(model) -> {score (0-100), rating, summary, evidence[]}`.
- Evidence format: list of dicts containing metric name, raw value, source, thresholds, per-metric 0-5 and 0-100 scores, and pass boolean.
- Aggregation: per-module final score is mean of per-metric 0–5 mapped to 0–100 (score*20).
- Overall:
  - Weighted average of module scores (weights from config).
  - Gate pass count computed against `pass_threshold` per module.
  - Confidence score = mean of module scores.
- Notes:
  - `backend/scoring/_utils.py` contains helpers `extract_series()` and `score_value_linear()`.
  - No thresholds are hard-coded in modules; all thresholds are in YAML config.

--------------------------------------------------------------------------------
9. Streamlit page structure
--------------------------------------------------------------------------------
Entry: `app/streamlit_app.py`
Pages (sidebar navigation):
- Analysis Panel — ticker input and "Analyze Company" button (runs analyze_company)
- Company Detail — displays CompanyFinancialModel, Nalanda Six Gates, Valuation, Investment Committee, AI Memo, Save to Research Journal
- Research Journal — lists saved analyses, allows loading saved research
- Evidence — raw evidence listing (mock/sample)

Streamlit responsibilities:
- Only render data returned by backend.services (no business logic in UI)
- Maintain session state for current_analysis and selected_company

--------------------------------------------------------------------------------
10. Configuration files
--------------------------------------------------------------------------------
- requirements.txt — runtime dependencies
- runtime.txt — python runtime (python-3.11.4)
- config/scoring_rules.yaml — scoring weights, metrics, thresholds, rating mapping

--------------------------------------------------------------------------------
11. Environment variables
--------------------------------------------------------------------------------
- FMP_API_KEY — Financial Modeling Prep API key (required for live FMP queries). Should be set in environment or Streamlit Secrets. No keys are committed.
- (future) OPENAI_API_KEY — for LLM integration (not used in deterministic AI memo generator)

--------------------------------------------------------------------------------
12. Known limitations
--------------------------------------------------------------------------------
- Valuation heuristics are simple and not sector-specific.
- Some metrics depend on the availability of provider data; Yahoo fallback may be incomplete.
- SQLite storage is local and ephemeral on some hosting; intended for single-user MVP.
- AI memo is deterministic rule-based; LLM synthesis planned in future.
- No concurrent user management or auth.

--------------------------------------------------------------------------------
13. Technical debt
--------------------------------------------------------------------------------
- Scoring modules use simple linear scaling; more robust statistical normalization (sector-adjusted percentiles) would improve accuracy.
- Connector error handling could be hardened (retry/backoff, rate-limit handling).
- CI tests and unit tests are not yet implemented (high priority).
- Migration to PostgreSQL/Supabase for production multi-user environment required.

--------------------------------------------------------------------------------
14. Deployment process
--------------------------------------------------------------------------------
1. Ensure runtime.txt and requirements.txt are at repo root.
2. Add secrets (FMP_API_KEY) in Streamlit Community Cloud.
3. Deploy in Streamlit Cloud; verify that pip installs wheels (no source builds for numpy/pandas).
4. Run smoke tests (analyze sample tickers) and verify Research Journal persistence.

Local dev:
 - python -m venv .venv
 - .venv\\Scripts\\activate (Windows) or source .venv/bin/activate
 - pip install -r requirements.txt
 - streamlit run app/streamlit_app.py

--------------------------------------------------------------------------------
15. Future extension points
--------------------------------------------------------------------------------
- Provider abstraction: implement `backend/connectors/*` interface and add adapters for AlphaVantage/Finnhub; `fetch_company_financials()` should be provider-agnostic.
- Replace deterministic memo with LLM pipeline that cites evidence IDs and stores provenance.
- Add unit tests for each scoring module and end-to-end integration tests.
- Add user authentication and multi-user persistence (Postgres).
- Add sector-adjusted percentile normalizers for scoring.
- Add scheduled data refresh and data warehouse pipeline for historical analyses.

--------------------------------------------------------------------------------
Appendix: Key code references
- Entrypoint: `app/streamlit_app.py`
- Orchestration: `backend/services.py`
- Connectors: `backend/connectors/fmp.py`
- Scoring modules: `backend/scoring/*.py`
- Config: `config/scoring_rules.yaml`
- DB schema: `backend/schema.sql`

For questions about a specific module, open the referenced file; the code is documented inline where necessary.

