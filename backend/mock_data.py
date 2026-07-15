import pandas as pd
from datetime import datetime, timedelta

def _make_hist_scores(seed: int = 70):
    today = datetime.utcnow().date()
    rows = []
    for i in range(12):
        d = today - timedelta(days=30*(11-i))
        rows.append({"date": d.isoformat(), "overall_score": float(max(40, min(95, seed + (i-6)*2)))})
    return pd.DataFrame(rows)

MOCK_COMPANIES = {
    "AAPL": {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "overall_score": 88.5,
        "status": "PASS",
        "last_updated": "2026-07-14",
        "quality_breakdown": [
            {"dimension": "Profitability", "score": 92.0, "short_explanation": "High ROE and stable margins", "evidence_refs":[1,2]},
            {"dimension": "Management Alignment", "score": 80.0, "short_explanation": "Insiders hold small equity", "evidence_refs":[3]},
            {"dimension": "Insider Activity", "score": 75.0, "short_explanation": "Mixed selling/compensation selling", "evidence_refs":[4]},
            {"dimension": "Competitive Moat", "score": 95.0, "short_explanation": "Strong brand & ecosystem", "evidence_refs":[5]},
            {"dimension": "Financial Strength", "score": 90.0, "short_explanation": "Low net debt, strong liquidity", "evidence_refs":[6]},
            {"dimension": "Cash Flow", "score": 94.0, "short_explanation": "Consistent FCF generation", "evidence_refs":[7]},
            {"dimension": "Growth", "score": 85.0, "short_explanation": "Solid revenue & EPS CAGR", "evidence_refs":[8]},
        ],
        "historical_trend": _make_hist_scores(86),
        "ai_summary": {
            "strengths": ["Excellent ROE consistency", "Strong free cash flow", "High switching cost in ecosystem"],
            "risks": ["Supply chain concentration", "Rising component costs"],
            "opinion": "Still satisfies Investment Quality Framework."
        },
        "evidence": [
            {"id":1,"metric_key":"10yr_ROE","metric_value":28.4,"source":"FMP","as_of_date":"2025-12-31","raw_json":"{...}"},
            {"id":2,"metric_key":"10yr_ROIC","metric_value":25.1,"source":"FMP","as_of_date":"2025-12-31","raw_json":"{...}"},
            {"id":3,"metric_key":"insider_ownership_pct","metric_value":1.2,"source":"SEC_EDGAR","as_of_date":"2026-03-31","raw_json":"{...}"},
            {"id":4,"metric_key":"insider_sells_count","metric_value":12,"source":"SEC_FORM4","as_of_date":"2026-06-30","raw_json":"{...}"},
            {"id":5,"metric_key":"moat_notes","metric_value":None,"source":"Annual_Report","as_of_date":"2025-09-30","raw_json":"{...}"},
            {"id":6,"metric_key":"net_debt","metric_value":-84000,"source":"FMP","as_of_date":"2025-12-31","raw_json":"{...}"},
            {"id":7,"metric_key":"fcf_trend_10y","metric_value":1.12,"source":"FMP","as_of_date":"2025-12-31","raw_json":"{...}"},
            {"id":8,"metric_key":"revenue_cagr_10y","metric_value":0.12,"source":"FMP","as_of_date":"2025-12-31","raw_json":"{...}"},
        ]
    },
    "MSFT": {
        "ticker": "MSFT",
        "company_name": "Microsoft Corp.",
        "overall_score": 91.2,
        "status": "PASS",
        "last_updated": "2026-07-13",
        "quality_breakdown": [
            {"dimension": "Profitability", "score": 94.0, "short_explanation": "High ROIC across segments", "evidence_refs":[11]},
            {"dimension": "Management Alignment", "score": 85.0, "short_explanation": "Strong insider ownership", "evidence_refs":[12]},
            {"dimension": "Insider Activity", "score": 78.0, "short_explanation": "Normal compensation selling", "evidence_refs":[13]},
            {"dimension": "Competitive Moat", "score": 92.0, "short_explanation": "Network effects in cloud", "evidence_refs":[14]},
            {"dimension": "Financial Strength", "score": 88.0, "short_explanation": "Healthy balance sheet", "evidence_refs":[15]},
            {"dimension": "Cash Flow", "score": 90.0, "short_explanation": "Robust operating cash flow", "evidence_refs":[16]},
            {"dimension": "Growth", "score": 86.0, "short_explanation": "Strong software & cloud growth", "evidence_refs":[17]},
        ],
        "historical_trend": _make_hist_scores(90),
        "ai_summary": {
            "strengths": ["High ROIC", "Recurring revenue", "Large enterprise moat"],
            "risks": ["Regulatory scrutiny", "Cloud competition"],
            "opinion": "Meets quality thresholds with minor governance notes."
        },
        "evidence": [
            {"id":11,"metric_key":"10yr_ROE","metric_value":30.2,"source":"FMP","as_of_date":"2025-12-31","raw_json":"{...}"},
            {"id":12,"metric_key":"insider_ownership_pct","metric_value":2.1,"source":"SEC_EDGAR","as_of_date":"2026-03-31","raw_json":"{...}"},
        ]
    }
}

def available_tickers():
    return list(MOCK_COMPANIES.keys())

def get_company(ticker):
    return MOCK_COMPANIES.get(ticker)

