from datetime import datetime, timezone


def utc_now():

    return datetime.now(timezone.utc)


def to_iso(dt: datetime):

    return dt.isoformat()