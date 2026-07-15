import streamlit as st
from pathlib import Path
import pandas as pd
# Ensure project root is on sys.path so sibling packages (backend) are importable when running via `streamlit run app/...`
import sys, os
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend import services

ROOT = Path(__file__).resolve().parent.parent

st.set_page_config(layout="wide", page_title="Nalanda Investment Quality Gate")

PAGES = ["Portfolio Overview", "Company Detail", "Evidence"]

def sidebar():
    st.sidebar.title("Nalanda IQG")
    page = st.sidebar.selectbox("Page", PAGES)
    st.sidebar.markdown("---")
    st.sidebar.markdown("Watchlist (manual input) — one ticker per line")
    watchlist = st.sidebar.text_area("Tickers", value="AAPL\nMSFT\n883.HK", height=120)
    tickers = [t.strip().upper() for t in watchlist.splitlines() if t.strip()]
    return page, tickers


def render_portfolio(tickers):
    st.header("Portfolio Overview")
    if not tickers:
        st.info("Enter tickers in the sidebar to populate the portfolio.")
        return

    # Fetch overview from backend service (mock data for MVP)
    overview = services.fetch_portfolio_overview(tickers)
    df = pd.DataFrame(overview)

    # display summary cards
    cols = st.columns(4)
    avg_score = df["overall_score"].mean() if not df["overall_score"].isnull().all() else None
    cols[0].metric("Stocks", len(df))
    cols[1].metric("Avg Quality", f"{avg_score:.1f}" if avg_score is not None else "N/A")
    cols[2].metric("PASS (Gate)", df[df["status"] == "PASS"].shape[0])
    cols[3].metric("BLOCK (Gate)", df[df["status"] == "BLOCK"].shape[0])

    st.markdown("### Watchlist")
    st.dataframe(df[["ticker", "company_name", "overall_score", "status", "last_updated"]], use_container_width=True)

    st.markdown("Select a company to view details")
    selection = st.selectbox("Company", options=df["ticker"].tolist())
    if selection:
        st.session_state.selected_company = selection


def render_company_detail(selected_ticker: str | None):
    st.header("Company Detail")
    if not selected_ticker:
        st.info("Select a company from the Portfolio Overview first.")
        return

    detail = services.fetch_company_detail(selected_ticker)
    if detail is None:
        st.error("Company not found in mock data.")
        return
    # Attempt to fetch FMP financials (if API key provided); display results or graceful error
    fin_res = services.fetch_company_financials(selected_ticker)
    if fin_res.get("ok"):
        model = fin_res["model"]
        scoring = fin_res.get("scoring", {})
        st.markdown("## Nalanda Scoring")
        overall_score = scoring.get("overall_score")
        rating = scoring.get("rating")
        cols = st.columns([2,1])
        cols[0].metric("Overall Score", f"{overall_score:.1f}/100" if overall_score is not None else "N/A")
        cols[1].markdown(f"**Rating:** {rating if rating else 'N/A'}")
        st.markdown("### Module breakdown")
        modules = scoring.get("modules", {})
        for mod_name, mod_res in modules.items():
            st.markdown(f"#### {mod_name.capitalize()} — {mod_res.get('score'):.1f}/100")
            st.write(mod_res.get("summary"))
            evid = mod_res.get("evidence", [])
            if evid:
                import pandas as _pd
                df_e = _pd.DataFrame(evid)
                # ensure columns exist
                cols_to_show = ["metric", "value", "best", "worst", "score_0_100", "pass", "source"]
                show_cols = [c for c in cols_to_show if c in df_e.columns]
                st.dataframe(df_e[show_cols], use_container_width=True)

        st.markdown("## Financials (Financial Modeling Prep)")
        # profile
        if model.profile:
            st.write("**Company Profile**")
            st.json(model.profile)
        # income statement
        if not model.income_statement.empty:
            st.markdown("**Income Statement (most recent rows)**")
            st.dataframe(model.income_statement.head(5), use_container_width=True)
        else:
            st.info("Income statement not available from FMP for this ticker.")

        if not model.balance_sheet.empty:
            st.markdown("**Balance Sheet (most recent rows)**")
            st.dataframe(model.balance_sheet.head(5), use_container_width=True)
        else:
            st.info("Balance sheet not available from FMP for this ticker.")

        if not model.cash_flow.empty:
            st.markdown("**Cash Flow (most recent rows)**")
            st.dataframe(model.cash_flow.head(5), use_container_width=True)
        else:
            st.info("Cash flow not available from FMP for this ticker.")

        if not model.financial_ratios.empty:
            st.markdown("**Financial Ratios (most recent rows)**")
            st.dataframe(model.financial_ratios.head(5), use_container_width=True)

        if not model.key_metrics.empty:
            st.markdown("**Key Metrics (most recent rows)**")
            st.dataframe(model.key_metrics.head(5), use_container_width=True)
    else:
        st.warning(f"FMP data not available: {fin_res.get('error')}")
    # Top row: Company name + overall score + status
    title_col, score_col, status_col = st.columns([3,1,1])
    title_col.subheader(f"{detail['ticker']} — {detail['company_name']}")
    score_col.metric("Overall Quality", f"{detail['overall_score']:.1f}/100")
    status_col.markdown(f"**Status:** {detail['status']}")

    st.markdown("### Quality Breakdown")
    dims = detail["quality_breakdown"]
    cols = st.columns(len(dims))
    for i, d in enumerate(dims):
        with cols[i]:
            st.metric(d["dimension"], f"{d['score']:.1f}/100")
            st.caption(d["short_explanation"])

    st.markdown("### Historical Quality Trend")
    hist = detail["historical_trend"]
    if isinstance(hist, pd.DataFrame) and not hist.empty:
        hist = hist.set_index("date")
        st.line_chart(hist["overall_score"])
    else:
        st.info("No historical trend available.")

    st.markdown("### AI Summary")
    st.write("**Strengths**")
    for s in detail["ai_summary"]["strengths"]:
        st.write(f"- {s}")
    st.write("**Risks**")
    for r in detail["ai_summary"]["risks"]:
        st.write(f"- {r}")
    st.write("**Overall Opinion**")
    st.write(detail["ai_summary"]["opinion"])

    st.markdown("### Evidence (sample)")
    ev_df = pd.DataFrame(detail["evidence"])
    st.dataframe(ev_df[["id", "metric_key", "metric_value", "source", "as_of_date"]], use_container_width=True)


def render_evidence():
    st.header("Evidence")
    st.info("Raw evidence used to compute scores. Each entry includes source and raw sample.")
    tickers = services.available_tickers()
    ticker = st.selectbox("Ticker", options=tickers)
    ev = services.fetch_evidence_for_ticker(ticker)
    if ev:
        st.dataframe(pd.DataFrame(ev), use_container_width=True)
    else:
        st.info("No evidence for selected ticker.")


def main():
    page, tickers = sidebar()
    if page == "Portfolio Overview":
        render_portfolio(tickers)
    elif page == "Company Detail":
        selected = st.session_state.get("selected_company", None)
        render_company_detail(selected)
    else:
        render_evidence()


if __name__ == "__main__":
    main()

