"""
Tests for _as_datetime (src/routers/activity.py).

Some rows in the database were written before the current save format,
so this app has to accept BOTH a real datetime and a leftover string like
"2025-05-14 09:31:29". This helper normalizes either into a real datetime
so the rest of the code doesn't have to care which one it got.
"""
from datetime import datetime

import pytest


def _as_datetime(value):
    """Copied from src/routers/activity.py so this test has no import
    dependency on the Flask app / database setup."""
    if isinstance(value, datetime):
        return value
    v = value.rstrip('Z').replace('T', ' ')
    return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')


def test_passes_through_a_real_datetime_unchanged():
    dt = datetime(2025, 5, 15, 10, 8, 9)
    assert _as_datetime(dt) is dt


def test_parses_a_space_separated_legacy_string():
    result = _as_datetime("2025-05-14 09:31:29")
    assert result == datetime(2025, 5, 14, 9, 31, 29)


def test_parses_a_strava_style_t_z_string():
    result = _as_datetime("2025-05-14T09:31:29Z")
    assert result == datetime(2025, 5, 14, 9, 31, 29)


def test_year_month_are_accessible_after_normalizing_either_format():
    as_dt = _as_datetime(datetime(2025, 3, 1, 0, 0, 0))
    as_str = _as_datetime("2025-03-01 00:00:00")
    assert as_dt.year == as_str.year == 2025
    assert as_dt.month == as_str.month == 3


def test_raises_a_clear_error_on_genuinely_malformed_input():
    with pytest.raises(ValueError):
        _as_datetime("not a date at all")
