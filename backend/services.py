import pandas as pd
from . import mock_data
from copy import deepcopy
from datetime import datetime
from .connectors import fmp
from .models import CompanyFinancialModel
import pandas as pd
from .scoring.overall import evaluate_overall
import yfinance as yf
import json
from .db import get_engine, init_db
from sqlalchemy import text
import re
from typing import Dict, Any, List

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


def normalize_ticker(raw: str) -> str:
    """Normalize user input to canonical ticker (append .HK for numeric tickers)."""
    if not raw or not isinstance(raw, str):
        return raw
    s = raw.strip().upper()
    # If already contains a dot (e.g., .HK) or hyphen, assume user provided suffix
    if "." in s or "-" in s:
        return s
    # If purely numeric -> HK stock
    if re.fullmatch(r"\d+", s):
        return f"{s}.HK"
    return s


def analyze_company(raw_ticker: str) -> dict:
    """
    High-level analysis flow:
    - normalize ticker
    - try FMP via fetch_company_financials (primary)
    - if FMP fails, fallback to yfinance
    - run scoring evaluate_overall
    - return {ok, provider, model, scoring}
    """
    t = normalize_ticker(raw_ticker)
    # Try FMP first
    try:
        res = fetch_company_financials(t)
        if res.get("ok"):
            res["provider"] = "FMP"
            # generate AI summary
            try:
                ai = generate_investment_summary(res.get("model"), res.get("scoring"))
                res["ai_summary"] = ai
            except Exception:
                res["ai_summary"] = {}
            return res
        # else fallthrough to Yahoo
    except Exception:
        pass

    # Yahoo fallback
    try:
        yf_t = yf.Ticker(t)
        info = yf_t.info if hasattr(yf_t, "info") else {}
        # financials, balance_sheet, cashflow are DataFrames (may be empty)
        fin = getattr(yf_t, "financials", None)
        bal = getattr(yf_t, "balance_sheet", None)
        cf = getattr(yf_t, "cashflow", None)
        # convert to DataFrame copies
        def to_df_safe(x):
            try:
                if x is None:
                    return pd.DataFrame()
                if hasattr(x, "T"):
                    return x.T.copy() if hasattr(x, "T") else pd.DataFrame(x)
                return pd.DataFrame(x)
            except Exception:
                return pd.DataFrame()

        model = CompanyFinancialModel(
            ticker=t,
            profile=info,
            income_statement=to_df_safe(fin),
            balance_sheet=to_df_safe(bal),
            cash_flow=to_df_safe(cf),
            financial_ratios=pd.DataFrame(),
            key_metrics=pd.DataFrame(),
            raw={"profile": info, "yf_raw": {}},
        )
        scoring = evaluate_overall(model)
        valuation = extract_valuation(model)
        valuation_score = compute_valuation_score(valuation)
        scoring["valuation_score"] = valuation_score
        recommendation = decision_from_quality_valuation(scoring.get("overall_score", 0.0), valuation_score)
        ai = generate_investment_summary(model, scoring)
        return {"ok": True, "provider": "YAHOO", "model": model, "scoring": scoring, "ai_summary": ai, "valuation": valuation, "valuation_score": valuation_score, "recommendation": recommendation}
    except Exception as e:
        return {"ok": False, "error": f"Fallback error: {e}"}


def save_analysis(model: CompanyFinancialModel, scoring: dict, ai_summary: dict = None, notes: str = "") -> dict:
    """
    Save analysis into SQLite research library.
    Returns {"ok": True, "company_id": id}
    """
    # ensure DB schema exists
    init_db()
    engine = get_engine()
    now = datetime.utcnow().isoformat()
    with engine.begin() as conn:
        # ensure DB initialized
        try:
            # insert or ignore company
            res = conn.execute(text("SELECT id FROM companies WHERE ticker = :t"), {"t": model.ticker})
            row = res.fetchone()
            if row:
                company_id = row[0]
                conn.execute(text("UPDATE companies SET name = :n, last_updated = :lu WHERE id = :id"),
                             {"n": model.profile.get("companyName") if model.profile and isinstance(model.profile, dict) else None,
                              "lu": now, "id": company_id})
            else:
                conn.execute(text("INSERT INTO companies (ticker, exchange, name, last_updated) VALUES (:t, :ex, :n, :lu)"),
                             {"t": model.ticker, "ex": None, "n": model.profile.get("companyName") if model.profile and isinstance(model.profile, dict) else None, "lu": now})
                res2 = conn.execute(text("SELECT id FROM companies WHERE ticker = :t"), {"t": model.ticker})
                company_id = res2.fetchone()[0]

        except Exception as e:
            return {"ok": False, "error": str(e)}

        # insert module scores
        modules = scoring.get("modules", {})
        for dim, res in modules.items():
            evidence_json = json.dumps(res.get("evidence", []))
            try:
                conn.execute(text(
                    "INSERT INTO quality_scores (company_id, dimension, score, explanation, evidence_ref, evaluated_at) VALUES (:cid, :dim, :score, :ex, :ev, :evat)"
                ), {"cid": company_id, "dim": dim, "score": float(res.get("score", 0.0)), "ex": res.get("summary"), "ev": evidence_json, "evat": now})
            except Exception:
                pass
        # insert overall as a quality_scores row
        try:
            conn.execute(text(
                "INSERT INTO quality_scores (company_id, dimension, score, explanation, evidence_ref, evaluated_at) VALUES (:cid, :dim, :score, :ex, :ev, :evat)"
            ), {"cid": company_id, "dim": "Overall", "score": float(scoring.get("overall_score", 0.0)), "ex": "Overall score", "ev": json.dumps(scoring.get("modules", {})), "evat": now})
        except Exception:
            pass
        # insert AI summary report if provided
        if ai_summary or notes:
            try:
                conn.execute(text("INSERT INTO ai_reports (company_id, report_type, content, created_at) VALUES (:cid, :rt, :ct, :ca)"),
                             {"cid": company_id, "rt": "investment_summary", "ct": json.dumps({"ai": ai_summary, "memo": ai_summary.get("memo") if ai_summary else None, "notes": notes}), "ca": now})
            except Exception:
                pass
        # insert research_journal entry (valuation and recommendation)
        try:
            valuation = scoring.get("valuation", {}) if isinstance(scoring, dict) else {}
            recommendation = scoring.get("recommendation") or (ai_summary.get("recommendation") if ai_summary else None)
            # create research_journal record
            conn.execute(text("INSERT INTO research_journal (company_id, analysis_date, quality_score, valuation_json, recommendation, ai_memo, notes, review_date) VALUES (:cid, :ad, :qs, :vj, :rec, :memo, :notes, :rev)"),
                         {"cid": company_id, "ad": now, "qs": float(scoring.get("overall_score", 0.0)), "vj": json.dumps(valuation), "rec": recommendation, "memo": ai_summary.get("memo") if ai_summary else None, "notes": notes, "rev": None})
        except Exception:
            pass
    return {"ok": True, "company_id": company_id}


def generate_investment_summary(model: CompanyFinancialModel, scoring: dict) -> Dict[str, Any]:
    """
    Lightweight rule-based AI summary generator. Produces recommendation, strengths, weaknesses, opinion.
    """
    out: Dict[str, Any] = {"recommendation": "WATCH", "strengths": [], "risks": [], "opinion": "", "memo": ""}
    overall = scoring.get("overall_score", 0.0) if scoring else 0.0
    # recommendation mapping
    if overall >= 75:
        out["recommendation"] = "PASS"
    elif overall >= 45:
        out["recommendation"] = "WATCH"
    else:
        out["recommendation"] = "REJECT"

    # simple heuristics from module scores
    modules = scoring.get("modules", {}) if scoring else {}
    # profitability
    pf = modules.get("profitability", {}).get("score", 0)
    if pf >= 80:
        out["strengths"].append("Strong profitability (ROE/ROIC).")
    elif pf < 40:
        out["risks"].append("Weak profitability.")
    # cashflow
    cf = modules.get("cashflow", {}).get("score", 0)
    if cf >= 80:
        out["strengths"].append("Robust free cash flow.")
    elif cf < 40:
        out["risks"].append("Weak cash conversion.")
    # debt
    db = modules.get("debt", {}).get("score", 0)
    if db < 40:
        out["risks"].append("High leverage or weak balance sheet.")
    # moat
    mo = modules.get("moat", {}).get("score", 0)
    if mo >= 80:
        out["strengths"].append("Strong competitive moat.")
    elif mo < 40:
        out["risks"].append("No clear moat.")

    # short opinion
    out["opinion"] = f"Overall score {overall:.1f}. Recommendation: {out['recommendation']}."
    # build AI memo
    company = model.profile.get("companyName") if model and model.profile and isinstance(model.profile, dict) else model.ticker if model else ""
    business = model.profile.get("industry") if model and model.profile and isinstance(model.profile, dict) else ""
    memo_lines: List[str] = []
    memo_lines.append(f"Company: {company}")
    memo_lines.append(f"Business: {business}")
    memo_lines.append("")
    memo_lines.append("Investment Thesis:")
    if out["strengths"]:
        for s in out["strengths"]:
            memo_lines.append(f"- {s}")
    else:
        memo_lines.append("- Further research required.")
    memo_lines.append("")
    memo_lines.append("Risks:")
    if out["risks"]:
        for r in out["risks"]:
            memo_lines.append(f"- {r}")
    else:
        memo_lines.append("- No immediate red flags detected.")
    memo_lines.append("")
    memo_lines.append("Recommendation:")
    memo_lines.append(out["recommendation"])
    memo = "\n".join(memo_lines)
    out["memo"] = memo
    return out


def extract_valuation(model: CompanyFinancialModel) -> Dict[str, Any]:
    """Extract valuation fields from model.profile or key_metrics or raw."""
    v: Dict[str, Any] = {}
    prof = getattr(model, "profile", {}) or {}
    km = getattr(model, "key_metrics", None)
    # common keys
    # try profile keys
    v["pe"] = prof.get("pe") or prof.get("peRatio") or prof.get("trailingPE")
    v["forward_pe"] = prof.get("forwardPE") or prof.get("forward_pe") or prof.get("forwardPE")
    v["peg"] = prof.get("pegRatio") or prof.get("peg")
    v["ev_ebitda"] = prof.get("enterpriseToEbitda") or prof.get("evToEbitda") or prof.get("enterpriseValueToEbitda")
    v["price_fcf"] = prof.get("priceToFreeCashflow") or prof.get("priceToFCF") or prof.get("priceToFreeCashFlow")
    v["div_yield"] = prof.get("dividendYield") or prof.get("dividendYieldPercent")
    # 52-week percentile: try compute from profile low/high if available
    try:
        low = prof.get("52WeekLow") or prof.get("fiftyTwoWeekLow")
        high = prof.get("52WeekHigh") or prof.get("fiftyTwoWeekHigh")
        price = prof.get("price") or prof.get("previousClose") or prof.get("last_price")
        if low and high and price and high > low:
            perc = (price - low) / (high - low) * 100
            v["52w_percentile"] = round(max(0.0, min(100.0, perc)), 2)
        else:
            v["52w_percentile"] = None
    except Exception:
        v["52w_percentile"] = None
    # fallback: check key_metrics DataFrame for fields
    if km is not None and not km.empty:
        for col in ["pe", "forward_pe", "peg", "ev_ebitda", "price_fcf", "div_yield", "52w_percentile"]:
            if v.get(col) is None and col in km.columns:
                try:
                    v[col] = float(km[col].astype(float).dropna().iloc[-1])
                except Exception:
                    v[col] = None
    return v


def compute_valuation_score(valuation: Dict[str, Any]) -> float:
    """Heuristic valuation scoring (0-100). Lower PE/EV/PriceFCF and lower 52w percentile => higher score."""
    score = 50.0
    # use 52w percentile if available
    p52 = valuation.get("52w_percentile")
    if p52 is not None:
        # cheaper percentile -> higher score
        score = max(0.0, min(100.0, 100.0 - float(p52)))
        return round(score, 2)
    # otherwise adjust from metrics
    try:
        fe = valuation.get("forward_pe")
        if fe is not None:
            fe = float(fe)
            if fe <= 10:
                score += 25
            elif fe <= 20:
                score += 10
            elif fe <= 40:
                score += 0
            else:
                score -= 20
        pfcf = valuation.get("price_fcf")
        if pfcf is not None:
            pfcf = float(pfcf)
            if pfcf <= 10:
                score += 20
            elif pfcf <= 20:
                score += 5
            elif pfcf <= 50:
                score += 0
            else:
                score -= 15
        ev = valuation.get("ev_ebitda")
        if ev is not None:
            ev = float(ev)
            if ev <= 8:
                score += 20
            elif ev <= 12:
                score += 5
            elif ev <= 20:
                score += 0
            else:
                score -= 15
        peg = valuation.get("peg")
        if peg is not None:
            peg = float(peg)
            if peg <= 1:
                score += 10
            elif peg <= 2:
                score += 3
            else:
                score -= 5
        dy = valuation.get("div_yield")
        if dy is not None:
            try:
                if float(dy) > 0.03:
                    score += 5
            except Exception:
                pass
    except Exception:
        pass
    return float(max(0.0, min(100.0, score)))


def decision_from_quality_valuation(quality_score: float, valuation_score: float) -> str:
    """Combine quality and valuation into categorical recommendation."""
    q = float(quality_score or 0.0)
    v = float(valuation_score or 50.0)
    # Strong Buy: high quality and attractive valuation
    if q >= 80 and v >= 60:
        return "Strong Buy"
    if q >= 65 and v >= 50:
        return "Buy"
    if q >= 50 and v >= 40:
        return "Watch"
    if q >= 40 and v >= 30:
        return "Hold"
    return "Avoid"


def get_research_library():
    engine = get_engine()
    out = []
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, ticker, name, last_updated FROM companies ORDER BY last_updated DESC")).fetchall()
        for r in rows:
            cid, ticker, name, last = r
            # fetch overall score if any
            sc = conn.execute(text("SELECT score, evaluated_at FROM quality_scores WHERE company_id = :cid AND dimension = 'Overall' ORDER BY evaluated_at DESC LIMIT 1"), {"cid": cid}).fetchone()
            overall = sc[0] if sc else None
            out.append({"company_id": cid, "ticker": ticker, "name": name, "last_updated": last, "overall_score": overall})
    return out


def load_saved_analysis(company_id: int):
    engine = get_engine()
    with engine.connect() as conn:
        comp = conn.execute(text("SELECT id, ticker, name, last_updated FROM companies WHERE id = :id"), {"id": company_id}).fetchone()
        if not comp:
            return None
        qs = conn.execute(text("SELECT dimension, score, explanation, evidence_ref, evaluated_at FROM quality_scores WHERE company_id = :cid ORDER BY evaluated_at DESC"), {"cid": company_id}).fetchall()
        modules = {}
        overall = None
        for row in qs:
            dim, score, ex, evref, evat = row
            try:
                ev = json.loads(evref) if evref else []
            except Exception:
                ev = []
            if dim == "Overall":
                overall = {"score": score, "evaluated_at": evat}
            else:
                modules[dim] = {"score": score, "summary": ex, "evidence": ev, "evaluated_at": evat}
        return {"company": {"id": comp[0], "ticker": comp[1], "name": comp[2], "last_updated": comp[3]}, "scoring": {"overall": overall, "modules": modules}}

