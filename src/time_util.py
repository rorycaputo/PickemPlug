import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LEAGUE_TZ = ZoneInfo('America/New_York')
DEFAULT_DISPLAY_TZ = 'America/Chicago'
DISPLAY_TZ_ENV = 'DISPLAY_TZ'


def get_display_tz() -> ZoneInfo:
    """Zone used only for showing times to the user, from DISPLAY_TZ (default Central)."""
    name = os.environ.get(DISPLAY_TZ_ENV) or DEFAULT_DISPLAY_TZ
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(f'{DISPLAY_TZ_ENV} is not a valid time zone name: {name!r}') from e


def now() -> datetime:
    """Current instant as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def parse_utc_iso(value: str) -> datetime:
    """Parse an ISO-8601 UTC string like 2026-11-13T01:15:00.0000000Z.

    Only the first 19 characters are used: Python 3.10's fromisoformat rejects the
    trailing 'Z' and the 6 or 7 fractional digits the sportsbooks send.
    """
    return datetime.strptime(value[:19], '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)


def to_display(dt: datetime) -> datetime:
    """Convert an aware datetime to the display zone."""
    return dt.astimezone(get_display_tz())
