try:
    import yaml
except Exception:
    yaml = None
from pathlib import Path
from functools import lru_cache

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "scoring_rules.yaml"


@lru_cache(maxsize=1)
def load_rules() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    if yaml is None:
        # PyYAML not installed in this environment; return empty rules
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_module_rules(module_name: str) -> dict:
    data = load_rules()
    return data.get("modules", {}).get(module_name, {})


def get_rating_config() -> dict:
    data = load_rules()
    return data.get("rating_stars", {})

