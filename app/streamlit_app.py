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

PAGES = ["Analysis Panel", "Company Detail", "Research Journal", "Evidence"]

def sidebar():
    st.sidebar.title("Nalanda IQG — Analysis Panel")
    page = st.sidebar.selectbox("Page", PAGES)
    st.sidebar.markdown("---")
    st.sidebar.markdown("Stock Symbol")
    ticker_in = st.sidebar.text_input("Enter ticker (e.g. AAPL or 883 for HK)", value="AAPL")
    if st.sidebar.button("Analyze Company"):
        # perform analysis via backend
        with st.spinner(f"Analyzing {ticker_in} ..."):
            res = services.analyze_company(ticker_in)
            st.session_state.current_analysis = res
            # set selected ticker for Company Detail page
            if res.get("ok"):
                st.session_state.selected_company = res.get("model").ticker
    return page, []


def render_portfolio(tickers):
    # Research Journal listing (previously Research Library)
    st.header("Research Journal")
    st.info("Previously saved analyses. Use 'Analyze Company' in sidebar to run fresh analyses (not saved).")
    rows = services.get_research_library()
    if not rows:
        st.info("No saved analyses yet.")
        return
    df = pd.DataFrame(rows)
    st.dataframe(df[["company_id", "ticker", "name", "overall_score", "last_updated"]], use_container_width=True)
    st.markdown("Select a saved analysis to view details")
    sel = st.selectbox("Saved company", options=[f"{r['company_id']} - {r['ticker']}" for r in rows])
    if sel:
        cid = int(sel.split(" - ")[0])
        # load saved analysis into session for viewing
        saved = services.load_saved_analysis(cid)
        st.session_state.current_analysis = {"ok": True, "provider": "SAVED", "model": None, "scoring": saved.get("modules") and {"overall_score": saved.get("overall", {}).get("score"), "modules": saved.get("modules", {})} or {}, "saved_company": saved.get("company")}
        st.session_state.selected_company = saved.get("company", {}).get("ticker")


def render_company_detail(selected_ticker: str | None):
    st.header("Company Detail")
    analysis = st.session_state.get("current_analysis")
    if not analysis:
        st.info("Run an analysis from the sidebar (enter symbol and click Analyze Company).")
        return
    if not analysis.get("ok"):
        st.error(f"Analysis failed: {analysis.get('error')}")
        return
    model = analysis.get("model")
    scoring = analysis.get("scoring", {})
    provider = analysis.get("provider")
    saved_company = analysis.get("saved_company")

    st.markdown(f"**Data provider:** {provider}")
    st.markdown("## Nalanda Scoring")
    overall_score = scoring.get("overall_score")
    rating = scoring.get("rating")
    cols = st.columns([2,1])
    cols[0].metric("Overall Score", f"{overall_score:.1f}/100" if overall_score is not None else "N/A")
    cols[1].markdown(f"**Rating:** {rating if rating else 'N/A'}")
    # Investment Committee summary
    st.markdown("## Investment Committee")
    ai = analysis.get("ai_summary", {})
    recommendation = ai.get("recommendation") if ai else None
    confidence = scoring.get("confidence")
    gates_passed = scoring.get("gates_passed", 0)
    total_gates = scoring.get("total_gates", 6)
    st.write(f"Recommendation: **{recommendation or 'N/A'}**")
    st.write(f"Confidence: **{confidence:.1f}**")
    st.write(f"Gates Passed: **{gates_passed} / {total_gates}**")
    st.markdown("**Key strengths**")
    for s in ai.get("strengths", []):
        st.write(f"- {s}")
    st.markdown("**Key weaknesses**")
    for r in ai.get("risks", []):
        st.write(f"- {r}")
    suggested = "Avoid"
    if recommendation == "PASS":
        suggested = "Buy / Accumulate"
    elif recommendation == "WATCH":
        suggested = "Wait for Pullback"
    elif recommendation == "REJECT":
        suggested = "Avoid"
    st.write(f"Suggested Action: **{suggested}**")
    st.markdown("### Module breakdown")
    # Nalanda Six Gates mapping
    gate_map = {
        "profitability": ("Gate 1\nReturn on Capital"),
        "management": ("Gate 2\nManagement Alignment"),
        "moat": ("Gate 3\nCompetitive Moat"),
        "debt": ("Gate 4\nFinancial Strength"),
        "cashflow": ("Gate 5\nCash Flow Quality"),
        "growth": ("Gate 6\nGrowth Quality"),
    }
    modules = scoring.get("modules", {})
    for key in ["profitability", "management", "moat", "debt", "cashflow", "growth"]:
        mod_res = modules.get(key, {})
        label = gate_map.get(key, (key.capitalize()))
        score = mod_res.get("score", 0.0) or 0.0
        stars = "★" * int(round(score/20))
        passed = mod_res.get("pass", False)
        status = "PASS" if passed else "FAIL"
        st.markdown(f"### {label}")
        st.write(f"{stars}  —  {score:.1f}/100  —  **{status}**")
        st.write(mod_res.get("summary", ""))
        df_e = pd.DataFrame(mod_res.get("evidence", []))
        if not df_e.empty:
            st.dataframe(df_e, use_container_width=True)

    st.markdown("## Financials")
    if model and getattr(model, "profile", None):
        st.write("**Company Profile**")
        st.json(model.profile)
    if model and getattr(model, "income_statement", None) is not None and not model.income_statement.empty:
        st.markdown("**Income Statement (most recent rows)**")
        st.dataframe(model.income_statement.head(5), use_container_width=True)
    if model and getattr(model, "balance_sheet", None) is not None and not model.balance_sheet.empty:
        st.markdown("**Balance Sheet (most recent rows)**")
        st.dataframe(model.balance_sheet.head(5), use_container_width=True)
    if model and getattr(model, "cash_flow", None) is not None and not model.cash_flow.empty:
        st.markdown("**Cash Flow (most recent rows)**")
        st.dataframe(model.cash_flow.head(5), use_container_width=True)

    st.markdown("### Evidence")
    if model and getattr(model, "raw", None):
        st.write(model.raw)
    for mod_name, mod_res in modules.items():
        st.markdown(f"**{mod_name} evidence**")
        df_e = pd.DataFrame(mod_res.get("evidence", []))
        if not df_e.empty:
            st.dataframe(df_e, use_container_width=True)

    st.markdown("### AI Investment Summary")
    ai = analysis.get("ai_summary", {})
    if ai:
        st.markdown(f"**Recommendation:** {ai.get('recommendation')}")
        st.markdown("**Key strengths**")
        for s in ai.get("strengths", []):
            st.write(f"- {s}")
        st.markdown("**Key weaknesses**")
        for r in ai.get("risks", []):
            st.write(f"- {r}")
        st.markdown("**Opinion**")
        st.write(ai.get("opinion"))

    notes = st.text_area("Notes (optional)", height=80)
    if st.button("Save to Research Journal"):
        res = services.save_analysis(model, scoring, ai_summary=ai, notes=notes)
        if res.get("ok"):
            st.success("Saved to Research Journal.")
        else:
            st.error(f"Save failed: {res.get('error')}")


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
    page, _ = sidebar()
    if page == "Analysis Panel":
        st.header("Analysis Panel")
        st.write("Enter a ticker in the sidebar and click 'Analyze Company' to run a live analysis. Results are not saved unless you click 'Save to Research Library'.")
        # show last analysis summary if exists
        analysis = st.session_state.get("current_analysis")
        if analysis and analysis.get("ok"):
            st.success("Last analysis available. Open Company Detail to view.")
    elif page == "Company Detail":
        selected = st.session_state.get("selected_company", None)
        render_company_detail(selected)
    elif page == "Research Library":
        render_portfolio([])
    else:
        render_evidence()


if __name__ == "__main__":
    main()

