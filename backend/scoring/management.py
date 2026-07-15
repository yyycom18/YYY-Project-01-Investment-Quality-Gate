from ..scoring.config import get_module_rules
from ._utils import extract_series, score_value_linear
from typing import Dict, Any
import numpy as np

def evaluate(model) -> Dict[str, Any]:
    rules = get_module_rules("management")
    metrics = rules.get("metrics", [])
    scores = []
    evidence = []
    for m in metrics:
        name = m.get("name")
        source = m.get("source")
        path = m.get("path")
        direction = m.get("direction", "higher_better")
        best = m.get("best")
        worst = m.get("worst")

        val = extract_series(model, source, path=path)
        if val is None:
            score_0_5 = 0.0
        else:
            try:
                score_0_5 = score_value_linear(float(val), best, worst, direction)
            except Exception:
                score_0_5 = 0.0
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
    return {"score": numeric, "rating": None, "summary": "Management alignment metrics.", "evidence": evidence}

