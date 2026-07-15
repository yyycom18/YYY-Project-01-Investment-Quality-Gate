from ..scoring.config import get_module_rules
from ._utils import extract_series, score_value_linear
from typing import Dict, Any
import numpy as np

def evaluate(model) -> Dict[str, Any]:
    rules = get_module_rules("cashflow")
    metrics = rules.get("metrics", [])
    scores = []
    evidence = []
    for m in metrics:
        name = m.get("name")
        source = m.get("source")
        field = m.get("field")
        agg = m.get("aggregate", "last")
        n = m.get("n", 5)
        direction = m.get("direction", "higher_better")
        best = m.get("best")
        worst = m.get("worst")

        series = extract_series(model, source, field=field)
        val = None
        if hasattr(series, "iloc"):
            if agg == "last":
                try:
                    val = float(series.astype(float).iloc[-1])
                except Exception:
                    val = None
            elif agg == "mean_last_n":
                try:
                    vals = series.astype(float).dropna().tail(n)
                    val = float(np.mean(vals)) if len(vals) else None
                except Exception:
                    val = None
        else:
            val = series

        if val is None:
            score_0_5 = 0.0
        else:
            score_0_5 = score_value_linear(val, best, worst, direction)
        scores.append(score_0_5)
        score_0_100 = round(score_0_5 * 20, 2)
        passed = score_0_5 >= 2.5
        evidence.append({
            "metric": name,
            "value": val,
            "source": source,
            "best": best,
            "worst": worst,
            "score_0_5": round(score_0_5,3),
            "score_0_100": score_0_100,
            "pass": passed
        })

    final_score = float(np.mean(scores)) if scores else 0.0
    numeric = round(final_score * 20, 2)
    return {"score": numeric, "rating": None, "summary": "Cash flow robustness.", "evidence": evidence}

