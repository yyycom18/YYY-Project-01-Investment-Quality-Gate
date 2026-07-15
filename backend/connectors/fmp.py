import os
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from ..cache import get_cache, set_cache
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv not available; environment must provide FMP_API_KEY
    def load_dotenv():
        return None

FMP_API_KEY = os.getenv("FMP_API_KEY")
FMP_BASE = "https://financialmodelingprep.com/api/v3"


def _make_cache_key(endpoint: str, params: Dict[str, Any]) -> str:
    key = endpoint + "|" + "|".join(f"{k}={v}" for k, v in sorted(params.items()))
    return key


def _get(endpoint: str, params: Optional[Dict[str, Any]] = None, ttl: int = 3600) -> Dict:
    """
    Low-level GET with file cache. Returns parsed JSON or raises RuntimeError on failure.
    """
    if params is None:
        params = {}
    if FMP_API_KEY:
        params["apikey"] = FMP_API_KEY
    url = f"{FMP_BASE}/{endpoint}"
    cache_key = _make_cache_key(url, params)
    cached = get_cache(cache_key, ttl_seconds=ttl)
    if cached is not None:
        return cached

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # store raw JSON
        set_cache(cache_key, data)
        return data
    except requests.HTTPError as e:
        raise RuntimeError(f"FMP HTTP error: {e} ({resp.status_code if 'resp' in locals() else 'n/a'})")
    except Exception as e:
        raise RuntimeError(f"FMP fetch error: {e}")


def income_statement(ticker: str, limit: int = 12) -> Dict:
    return _get(f"income-statement/{ticker}", params={"limit": limit})


def balance_sheet(ticker: str, limit: int = 12) -> Dict:
    return _get(f"balance-sheet-statement/{ticker}", params={"limit": limit})


def cash_flow_statement(ticker: str, limit: int = 12) -> Dict:
    return _get(f"cash-flow-statement/{ticker}", params={"limit": limit})


def financial_ratios(ticker: str, limit: int = 12) -> Dict:
    return _get(f"ratios/{ticker}", params={"limit": limit})


def key_metrics(ticker: str, limit: int = 12) -> Dict:
    return _get(f"key-metrics/{ticker}", params={"limit": limit})


def profile(ticker: str) -> Dict:
    return _get(f"profile/{ticker}", params={})

