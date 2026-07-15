from typing import Any, Dict
import pandas as pd

def extract_series(model, source: str, field: str = None, path: str = None):
    """
    Extract pandas Series or scalar from the CompanyFinancialModel according to source.
    Supports 'income_statement','balance_sheet','cash_flow','financial_ratios','key_metrics','raw','profile'.
    """
    src = source.lower()
    if src in ("income_statement", "balance_sheet", "cash_flow", "financial_ratios", "key_metrics"):
        df = getattr(model, src, None)
        if df is None or df.empty:
            return pd.Series(dtype=float)
        if field is None:
            return df
        # try lowercase column match
        cols = [c for c in df.columns if str(c).lower() == field.lower()]
        if not cols:
            # attempt direct access
            if field in df.columns:
                return df[field]
            return pd.Series(dtype=float)
        return df[cols[0]]
    if src == "raw" or src == "profile":
        # path like profile.companyInsiderOwnership or raw_moat_score
        obj = model.profile if src == "profile" else model.raw
        if obj is None:
            return None
        if path is None:
            return obj
        # support dotted path
        parts = path.split(".")
        cur = obj
        try:
            for p in parts:
                if isinstance(cur, dict):
                    cur = cur.get(p)
                else:
                    cur = getattr(cur, p, None)
            return cur
        except Exception:
            return None
    return None


def score_value_linear(value: float, best: float, worst: float, direction: str = "higher_better") -> float:
    """
    Map a raw numeric value to 0.0-5.0 scale via linear interpolation between worst and best.
    direction: 'higher_better' or 'lower_better'
    """
    try:
        v = float(value)
    except Exception:
        return 0.0
    if direction == "higher_better":
        if v <= worst:
            return 0.0
        if v >= best:
            return 5.0
        # linear between worst..best
        return 5.0 * (v - worst) / (best - worst) if best != worst else 0.0
    else:
        # lower is better: invert
        if v >= worst:
            return 0.0
        if v <= best:
            return 5.0
        return 5.0 * (worst - v) / (worst - best) if worst != best else 0.0

