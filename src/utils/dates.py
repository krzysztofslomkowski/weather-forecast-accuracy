"""Minimal date utilities shared across project scripts."""

from datetime import date


def today_utc() -> date:
    """Return today's date in UTC context (date-only)."""
    return date.today()
