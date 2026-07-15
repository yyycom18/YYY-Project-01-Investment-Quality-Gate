from . import profitability, management, moat, debt, cashflow, growth
from .config import get_module_rules, get_rating_config, load_rules as _load_rules
from typing import Dict, Any
import importlib

MODULE_MAP = {
    "profitability": profitability,
    "management": management,
    "moat": moat,
    "debt": debt,
    "cashflow": cashflow,
    "growth": growth,
}

def evaluate_overall(model) -> Dict[str, Any]:
    # ensure rules loaded
    rules = _load_rules()
    modules_cfg = rules.get("modules", {})
    results = {}
    weighted_scores = []
    total_weight = 0.0
    for name, mod in MODULE_MAP.items():
        cfg = modules_cfg.get(name, {})
        weight = cfg.get("weight", 1.0)
        try:
            res = mod.evaluate(model)
        except Exception as e:
            res = {"score": 0.0, "rating": None, "summary": f"Error evaluating: {e}", "evidence": []}
        results[name] = res
        score = res.get("score", 0.0) or 0.0
        weighted_scores.append(score * weight)
        total_weight += weight

    overall_score = round(sum(weighted_scores) / total_weight, 2) if total_weight else 0.0

    # map to stars using rating config
    rating_conf = get_rating_config().get("thresholds", {})
    star = None
    try:
        # thresholds: map numeric threshold -> star string
        for th, label in sorted(rating_conf.items(), key=lambda x: int(x[0]), reverse=True):
            if overall_score >= int(th):
                star = label
                break
    except Exception:
        star = None

    return {"overall_score": overall_score, "rating": star, "modules": results}

