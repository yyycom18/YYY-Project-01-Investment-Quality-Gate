import json
from pathlib import Path
import time
import hashlib
from typing import Optional

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{h}.json"


def get_cache(key: str, ttl_seconds: int = 3600) -> Optional[dict]:
    p = _cache_path(key)
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        ts = raw.get("_ts", 0)
        if time.time() - ts > ttl_seconds:
            try:
                p.unlink()
            except Exception:
                pass
            return None
        return raw.get("data")
    except Exception:
        return None


def set_cache(key: str, data: dict) -> None:
    p = _cache_path(key)
    payload = {"_ts": int(time.time()), "data": data}
    try:
        p.write_text(json.dumps(payload), encoding="utf-8")
    except Exception:
        pass

