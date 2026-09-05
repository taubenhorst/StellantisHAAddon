"""Default time zone comes from the TZ env var the Supervisor passes in."""
import os
from datetime import timezone
from zoneinfo import ZoneInfo


def get_default_time_zone():
    tz = os.environ.get("TZ")
    if tz:
        try:
            return ZoneInfo(tz)
        except Exception:
            pass
    return timezone.utc
