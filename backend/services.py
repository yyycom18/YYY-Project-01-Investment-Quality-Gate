import pandas as pd
from . import mock_data
from copy import deepcopy
from datetime import datetime
from .connectors import fmp
from .models import CompanyFinancialModel
import pandas as pd
from .scoring.overall import evaluate_overall

def fetch_portfolio_overview(tickers):
    """
    Return a list of overview dicts for tickers.
    Business logic is kept here (mock); Streamlit only renders results.
    """
    out = []
    for t in tickers:
        t = t.upper()
        c = mock_data.get_company(t)
        if c is None:
            out.append({
                "ticker": t,
                "company_name": None,
                "overall_score": float("nan"),
                "status": "UNKNOWN",
                "last_updated": None
            })
        else:
            out.append({
                "ticker": c["ticker"],
                "company_name": c["company_name"],
                "overall_score": c["overall_score"],
                "status": c["status"],
                "last_updated": c.get("last_updated", datetime.utcnow().date().isoformat())
            })
    return out

def fetch_company_detail(ticker):
    t = ticker.upper()
    c = mock_data.get_company(t)
    if c is None:
        return None
    # Return deep copy to avoid UI accidental mutation
    detail = deepcopy(c)
    # ensure historical_trend is a DataFrame
    if isinstance(detail.get("historical_trend"), pd.DataFrame):
        detail["historical_trend"] = detail["historical_trend"].copy()
    else:
        detail["historical_trend"] = pd.DataFrame()
    return detail


def fetch_company_financials(ticker: str) -> dict:
    """
    Fetch company financials from FMP and map into CompanyFinancialModel.
    Returns dict: { 'ok': True, 'model': CompanyFinancialModel } or { 'ok': False, 'error': msg }
    """
    t = ticker.upper()
    try:
        prof = fmp.profile(t)
        inc = fmp.income_statement(t, limit=12)
        bal = fmp.balance_sheet(t, limit=12)
        cf = fmp.cash_flow_statement(t, limit=12)
        ratios = fmp.financial_ratios(t, limit=12)
        km = fmp.key_metrics(t, limit=12)

        # convert lists to DataFrames when possible
        def to_df(x):
            if x is None:
                return pd.DataFrame()
            if isinstance(x, list):
                return pd.DataFrame(x)
            if isinstance(x, dict):
                # some endpoints return dict with 'financials' key
                if "financials" in x and isinstance(x["financials"], list):
                    return pd.DataFrame(x["financials"])
                return pd.DataFrame([x])
            return pd.DataFrame()

        model = CompanyFinancialModel(
            ticker=t,
            profile=prof if isinstance(prof, dict) else None,
            income_statement=to_df(inc),
            balance_sheet=to_df(bal),
            cash_flow=to_df(cf),
            financial_ratios=to_df(ratios),
            key_metrics=to_df(km),
            raw={"profile": prof, "income": inc, "balance": bal, "cash": cf, "ratios": ratios, "key_metrics": km},
        )
        # run scoring engine (overall) and attach results
        scoring = evaluate_overall(model)
        return {"ok": True, "model": model, "scoring": scoring}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def available_tickers():
    return mock_data.available_tickers()

def fetch_evidence_for_ticker(ticker):
    t = ticker.upper()
    c = mock_data.get_company(t)
    if c is None:
        return []
    return deepcopy(c.get("evidence", []))

