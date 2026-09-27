"""
Tests for training_load.py: TRIMP (Banister) and ACWR (Gabbett).

These are pure functions with no side effects, so they're tested the same
way the rest of this suite tests calculation helpers: real inputs, real
assertions, no mocking.
"""
from datetime import datetime, timedelta

import pytest

from src.utils import training_load as tl


# ---------- calculate_trimp ----------

def test_trimp_scores_higher_intensity_more_per_minute():
    # same 30-minute duration, but one run is at a much higher heart rate --
    # TRIMP's whole point is that this should score meaningfully more,
    # not just proportionally more.
    easy = tl.calculate_trimp(1800, 130, resting_hr=50, max_hr=190)
    hard = tl.calculate_trimp(1800, 170, resting_hr=50, max_hr=190)
    assert hard > easy * 1.5


def test_trimp_scores_longer_runs_higher_at_equal_intensity():
    short = tl.calculate_trimp(1800, 150, resting_hr=50, max_hr=190)   # 30 min
    long_ = tl.calculate_trimp(3600, 150, resting_hr=50, max_hr=190)   # 60 min
    assert long_ == pytest.approx(short * 2)


def test_trimp_returns_none_when_heart_rate_missing():
    assert tl.calculate_trimp(1800, None, resting_hr=50, max_hr=190) is None


def test_trimp_returns_none_when_resting_or_max_hr_missing():
    assert tl.calculate_trimp(1800, 150, resting_hr=None, max_hr=190) is None
    assert tl.calculate_trimp(1800, 150, resting_hr=50, max_hr=None) is None


def test_trimp_returns_none_instead_of_crashing_on_a_bad_hr_range():
    # resting >= max would divide by zero or go negative -- guard, don't crash
    assert tl.calculate_trimp(1800, 150, resting_hr=190, max_hr=50) is None
    assert tl.calculate_trimp(1800, 150, resting_hr=190, max_hr=190) is None


def test_trimp_returns_none_for_zero_or_negative_duration():
    assert tl.calculate_trimp(0, 150, resting_hr=50, max_hr=190) is None
    assert tl.calculate_trimp(-100, 150, resting_hr=50, max_hr=190) is None


def test_trimp_clamps_an_average_hr_reported_below_resting():
    # a device glitch, not a real negative-intensity run -- should clamp to
    # 0 relative intensity rather than go negative
    result = tl.calculate_trimp(1800, 40, resting_hr=50, max_hr=190)
    assert result == 0.0


def test_trimp_clamps_an_average_hr_reported_above_max():
    # clamped to 1.0 relative intensity, not an exploding exponential
    at_max = tl.calculate_trimp(1800, 190, resting_hr=50, max_hr=190)
    above_max = tl.calculate_trimp(1800, 220, resting_hr=50, max_hr=190)
    assert above_max == at_max


# ---------- calculate_acwr ----------

class _FakeActivity:
    """Minimal stand-in for the real Activity model -- only the fields
    calculate_acwr actually reads."""
    def __init__(self, days_ago, moving_time, average_heartrate, as_of=None):
        as_of = as_of or datetime.utcnow()
        self.start_date = as_of - timedelta(days=days_ago)
        self.moving_time = moving_time
        self.average_heartrate = average_heartrate


class _FakeActivityStrDate:
    """Same as _FakeActivity, but start_date is a string -- matching the
    real Activity table, where start_date is a plain String column."""
    def __init__(self, days_ago, moving_time, average_heartrate, as_of=None):
        as_of = as_of or datetime.utcnow()
        dt = as_of - timedelta(days=days_ago)
        self.start_date = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.moving_time = moving_time
        self.average_heartrate = average_heartrate


def _steady_training(as_of, weeks=4, runs_per_week=3, moving_time=1800, hr=150):
    # runs land on days 1, 3, 5 of each week -- kept clear of the day-7/day-28
    # window boundaries (calculate_acwr's windows are inclusive) so this
    # fixture means exactly "3 evenly-spaced runs per week", nothing on the
    # edge of tipping into or out of a window.
    activities = []
    for week in range(weeks):
        for run in range(runs_per_week):
            day_offset = week * 7 + run * 2 + 1
            activities.append(_FakeActivity(day_offset, moving_time, hr, as_of=as_of))
    return activities


def test_acwr_is_close_to_one_for_steady_unchanging_training():
    as_of = datetime.utcnow()
    activities = _steady_training(as_of)
    result = tl.calculate_acwr(activities, resting_hr=50, max_hr=190, as_of=as_of)
    assert result is not None
    assert result.ratio == pytest.approx(1.0, abs=0.05)
    assert result.band == "safe"


def test_acwr_flags_high_risk_after_a_sudden_volume_spike():
    as_of = datetime.utcnow()
    activities = _steady_training(as_of)
    # pile on hard, long runs every day this week on top of the steady base
    for day in range(6):
        activities.append(_FakeActivity(day, 3600, 175, as_of=as_of))
    result = tl.calculate_acwr(activities, resting_hr=50, max_hr=190, as_of=as_of)
    assert result.ratio > 1.5
    assert result.band == "high"


def test_acwr_flags_low_when_acute_load_drops_well_below_chronic():
    as_of = datetime.utcnow()
    # chronic history in weeks 2-4, nothing at all in the last 7 days
    # (e.g. recovering from a taper or a break)
    activities = [
        _FakeActivity(days_ago, 1800, 150, as_of=as_of)
        for days_ago in (10, 14, 17, 21, 24, 27)
    ]
    result = tl.calculate_acwr(activities, resting_hr=50, max_hr=190, as_of=as_of)
    assert result.acute_load == 0
    assert result.band == "low"


def test_acwr_returns_none_when_no_activity_has_heart_rate_data():
    as_of = datetime.utcnow()
    activities = [
        _FakeActivity(1, 1800, None, as_of=as_of),
        _FakeActivity(3, 1800, None, as_of=as_of),
    ]
    assert tl.calculate_acwr(activities, resting_hr=50, max_hr=190, as_of=as_of) is None


def test_acwr_returns_none_for_an_empty_activity_list():
    assert tl.calculate_acwr([], resting_hr=50, max_hr=190) is None


def test_acwr_ignores_runs_older_than_28_days():
    as_of = datetime.utcnow()
    activities = [
        _FakeActivity(2, 1800, 150, as_of=as_of),
        _FakeActivity(100, 1800, 150, as_of=as_of),  # way outside the window
    ]
    result = tl.calculate_acwr(activities, resting_hr=50, max_hr=190, as_of=as_of)
    assert result.runs_used == 1


def test_acwr_skips_runs_with_no_heart_rate_but_still_counts_the_rest():
    as_of = datetime.utcnow()
    activities = [
        _FakeActivity(1, 1800, 150, as_of=as_of),
        _FakeActivity(2, 1800, None, as_of=as_of),  # no HR -- e.g. a treadmill run logged manually
        _FakeActivity(3, 1800, 150, as_of=as_of),
    ]
    result = tl.calculate_acwr(activities, resting_hr=50, max_hr=190, as_of=as_of)
    assert result.runs_used == 2
    assert result.runs_skipped_no_hr == 1


def test_acwr_does_not_crash_when_start_date_is_a_string():
    # the real Activity table stores start_date as a String column, not a
    # datetime -- this is the exact bug that crashed the route in production
    as_of = datetime.utcnow()
    activities = [
        _FakeActivityStrDate(1, 1800, 150, as_of=as_of),
        _FakeActivityStrDate(3, 1800, 150, as_of=as_of),
        _FakeActivityStrDate(20, 1800, 150, as_of=as_of),
    ]
    result = tl.calculate_acwr(activities, resting_hr=50, max_hr=190, as_of=as_of)
    assert result is not None
    assert result.runs_used == 3


def test_acwr_gives_the_same_result_for_string_and_datetime_start_dates():
    as_of = datetime.utcnow()
    as_datetimes = [_FakeActivity(d, 1800, 150, as_of=as_of) for d in (1, 3, 20)]
    as_strings = [_FakeActivityStrDate(d, 1800, 150, as_of=as_of) for d in (1, 3, 20)]

    result_dt = tl.calculate_acwr(as_datetimes, resting_hr=50, max_hr=190, as_of=as_of)
    result_str = tl.calculate_acwr(as_strings, resting_hr=50, max_hr=190, as_of=as_of)

    assert result_dt.ratio == result_str.ratio
    assert result_dt.acute_load == result_str.acute_load
    assert result_dt.chronic_load == result_str.chronic_load


@pytest.mark.parametrize("ratio_target,expected_band", [
    (0.5, "low"),
    (1.0, "safe"),
    (1.4, "caution"),
    (2.0, "high"),
])
def test_risk_band_thresholds_match_the_gabbett_bands(ratio_target, expected_band):
    assert tl._risk_band(ratio_target) == expected_band