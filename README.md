# Nalanda Investment Research Terminal — v1.0

Nalanda is an AI-assisted Investment Research Workspace designed to help long-term investors analyze public companies using a structured, explainable framework. This project focuses on research workflows, evidence-backed scoring, valuation, AI memos, and a Research Journal for decision traceability.

Project overview
----------------
- Purpose: provide a single workspace to analyze companies and document investment decisions using the Nalanda framework.
- Not a trading bot or buy/sell signal machine — a decision support terminal.

Features (v1.0)
---------------
- Analysis Panel (on-demand analyses; FMP primary, Yahoo fallback)\n+- Nalanda Six Gates quality scoring (configurable)\n+- Valuation snapshot (PE, Forward PE, PEG, EV/EBITDA, Price/FCF, Dividend Yield, 52w percentile)\n+- Investment Committee (recommendation, confidence, gates passed, suggested action)\n+- AI Investment Memo (concise memo saved with research)\n+- Research Journal (persistent analyses with notes & evidence)\n+
Architecture
------------
- app/ — Streamlit UI (presentation only)\n+- backend/ — services, scoring, connectors, DB\n+- backend/connectors — FMP connector + Yahoo fallback\n+- backend/scoring — modular scoring engine (config-driven)\n+- config/ — scoring_rules.yaml\n+- data/ — runtime cache & SQLite DB\n+
Folder structure
----------------
```\n+app/\n+backend/\n+config/\n+data/\n+docs/\n+agents/\n+requirements.txt\n+runtime.txt\n+VERSION\n+CHANGELOG.md\n+RELEASE_NOTES.md\n+```\n+
Installation guide
------------------\n+1. Create & activate venv\n+   - Windows: `python -m venv .venv && .venv\\Scripts\\activate`\n+   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`\n+2. Install deps: `pip install -r requirements.txt`\n+3. (Optional) Set `FMP_API_KEY` in environment or Streamlit Secrets.\n+\n+Run locally\n+-----------\n+From repo root:\n+```\n+streamlit run app/streamlit_app.py\n+```\n+\n+Streamlit deployment guide\n+--------------------------\n+1. Push repo to GitHub.\n+2. Create Streamlit Community Cloud app and link repo.\n+3. Ensure `runtime.txt` and `requirements.txt` are at repo root.\n+4. Add `FMP_API_KEY` to Streamlit Secrets.\n+\n+Data sources\n+------------\n+- Financial Modeling Prep (primary)\n+- Yahoo Finance (fallback)\n+- SEC EDGAR / HKEX (documents — future)\n+\n+Current limitations\n+-------------------\n+- Simple valuation heuristics; tuning recommended by sector.\n+- Cache and SQLite are local/ephemeral on some hosting.\n+- AI memo is generated via deterministic rules (LLM integration planned).\n+\n+Roadmap\n+-------\n+- Historical charts (10-year metrics)\n+- Document scraping & transcript processing\n+- LLM-guided evidence-cited memos\n+- Multi-user persistence & PostgreSQL\n+\n+License: MIT\n+\n*** End Patch"}}
