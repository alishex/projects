from datetime import timedelta, datetime

import pytz

from app.config import TIMEZONE

TZ = pytz.timezone(TIMEZONE)

PERIOD_LABELS = {"day": "Кунлик", "week": "Ҳафталик", "month": "Ойлик"}


def now() -> datetime:
    return datetime.now(TZ)


def period_bounds(period: str):
    n = now()
    if period == "day":
        start = n.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (n - timedelta(days=n.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Номаълум давр: {period}")
    return start, n


def fmt_sum(tiyin: int) -> str:
    som = tiyin / 100
    if som == int(som):
        return f"{int(som):,}".replace(",", " ") + " сўм"
    return f"{som:,.2f}".replace(",", " ") + " сўм"


def fmt_usd(cents: int) -> str:
    return f"${cents / 100:,.2f}"
