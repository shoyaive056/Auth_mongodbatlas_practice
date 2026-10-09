from datetime import datetime, timezone


def utcnow() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """MongoDB may hand back naive datetimes; treat them as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
