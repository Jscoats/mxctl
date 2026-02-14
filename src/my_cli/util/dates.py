"""Date parsing and conversion helpers."""

from __future__ import annotations

from datetime import datetime, timedelta

from my_cli.util.formatting import die


def parse_date(date_str: str) -> datetime:
    """Parse YYYY-MM-DD string."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        die(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD (e.g. 2026-02-14).")


def to_applescript_date(dt: datetime) -> str:
    """Convert datetime to AppleScript date string (e.g. 'January 15, 2026')."""
    return dt.strftime("%B %d, %Y")


def days_ago(n: int) -> str:
    """Return YYYY-MM-DD for N days ago."""
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def today() -> str:
    """Return today as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def parse_applescript_date(date_str: str) -> str:
    """Parse AppleScript date to ISO 8601 format.

    Converts dates like:
    - "Tuesday, January 14, 2026 at 2:30:00 PM" → "2026-01-14T14:30:00"
    - "January 14, 2026 at 2:30:00 PM" → "2026-01-14T14:30:00"

    Returns original string if parsing fails (don't crash).
    """
    # Try with weekday first
    for fmt in [
        "%A, %B %d, %Y at %I:%M:%S %p",  # With weekday
        "%B %d, %Y at %I:%M:%S %p",  # Without weekday
    ]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue

    # Return original if parsing fails
    return date_str
