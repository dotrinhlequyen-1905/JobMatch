from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc)


def aware(value):
    return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)
