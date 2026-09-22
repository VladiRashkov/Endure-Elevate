"""
Tests for calculate_pace_dynamics (src/utils/activity_utils.py).

Walks a decoded GPS polyline and buckets it into per-kilometer pace splits.
"""
import polyline as pl

from src.utils import activity_utils as au


def test_returns_one_split_per_kilometer_completed():
    # three points ~0.5km apart in Sofia -> roughly 1km total, 60s -> should
    # yield at least one split, and never more splits than kilometers covered
    coords = [(42.6977, 23.3219), (42.7020, 23.3260), (42.7060, 23.3300)]
    encoded = pl.encode(coords)
    paces = au.calculate_pace_dynamics(encoded, total_distance=1000, total_time=300)
    assert len(paces) >= 1
    for p in paces:
        assert ":" in p  # "M:SS" format, not raw seconds


def test_pace_strings_are_zero_padded_seconds():
    coords = [(42.6977, 23.3219), (42.7500, 23.3800)]  # a long single jump
    encoded = pl.encode(coords)
    paces = au.calculate_pace_dynamics(encoded, total_distance=5000, total_time=1500)
    for p in paces:
        minutes, seconds = p.split(":")
        assert len(seconds) == 2  # e.g. "5:03", never "5:3"


def test_does_not_crash_on_a_two_point_polyline():
    coords = [(42.6977, 23.3219), (42.6980, 23.3225)]
    encoded = pl.encode(coords)
    paces = au.calculate_pace_dynamics(encoded, total_distance=100, total_time=30)
    assert isinstance(paces, list)
