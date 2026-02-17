import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger


@dataclass
class AppState:
    cookie_count: int = 0
    cookie_domains: list[str] = field(default_factory=list)
    cookies_expired: bool = False
    cookies_loaded_at: Optional[str] = None
    last_activation_time: Optional[str] = None
    last_activation_result: Optional[dict] = None
    next_scheduled_run: Optional[str] = None
    last_keepalive_time: Optional[str] = None
    last_keepalive_ok: bool = False
    is_running: bool = False


app_state = AppState()


def extract_cookie_metadata(path: Path) -> dict:
    """Extract ONLY safe metadata from cookies.json.

    Reads only: domain, expirationDate, session status.
    NEVER reads: name, value, or any token fields.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Cannot read cookie metadata: {e}")
        return {"count": 0, "domains": [], "expired_count": 0, "session_cookie_count": 0}

    if not isinstance(raw, list):
        return {"count": 0, "domains": [], "expired_count": 0, "session_cookie_count": 0}

    domains = set()
    expired_count = 0
    session_cookie_count = 0
    now = time.time()

    for cookie in raw:
        if not isinstance(cookie, dict):
            continue
        domain = cookie.get("domain", "")
        if domain:
            domains.add(domain)

        expiration = cookie.get("expirationDate")
        if expiration is None or cookie.get("session", False):
            session_cookie_count += 1
        elif isinstance(expiration, (int, float)) and expiration < now:
            expired_count += 1

    return {
        "count": len(raw),
        "domains": sorted(domains),
        "expired_count": expired_count,
        "session_cookie_count": session_cookie_count,
    }
