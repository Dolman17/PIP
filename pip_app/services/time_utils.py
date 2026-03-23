from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# -------------------------------------------
# Timezone helpers (robust on Windows)
# -------------------------------------------
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception

if ZoneInfo is not None:
    try:
        LONDON_TZ = ZoneInfo("Europe/London")
    except Exception:
        LONDON_TZ = timezone.utc
else:
    LONDON_TZ = timezone.utc


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return datetime.now(LONDON_TZ)


def today_local() -> date:
    return now_local().date()


def auto_review_date(start_date_str: str | None) -> str | None:
    if not start_date_str:
        return None
    try:
        dt = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
        return (dt + timedelta(days=28)).isoformat()
    except Exception:
        return None