"""
Tests for best_efforts.py: the fastest N-km stretch within a single run,
found by a sliding window over the per-kilometer splits.
"""
import pytest

import best_efforts as be


# ---------- _pace_str_to_seconds ----------

def test_pace_str_to_seconds_parses_mm_ss():
    assert be._pace_str_to_seconds("5:03") == 303


def test_pace_str_to_seconds_handles_single_digit_seconds():
    assert be._pace_str_to_seconds("4:05") == 245


# ---------- find_best_efforts ----------

def test_finds_the_fastest_single_kilometer():
    # the fastest 1K is just the single fastest split
    splits = ["5:10", "5:05", "4:35", "4:38", "5:20"]
    results = be.find_best_efforts(splits, target_distances_km=(1,))
    assert results[1].time_seconds == 275  # 4:35
    assert results[1].start_km == 2


def test_finds_the_fastest_multi_km_window_not_just_the_fastest_single_km():
    # the single fastest km is at index 3, but the fastest 3-KM *window*
    # is elsewhere -- a sliding window has to consider sums, not just the
    # single best split
    splits = ["6:00", "4:00", "4:00", "3:50", "6:00", "6:00"]
    results = be.find_best_efforts(splits, target_distances_km=(3,))
    # window [4:00, 4:00, 3:50] starting at index 1 beats any other 3-window
    assert results[3].start_km == 1
    assert results[3].time_seconds == be._pace_str_to_seconds("4:00") * 2 + be._pace_str_to_seconds("3:50")


def test_matches_brute_force_sum_over_all_windows():
    splits = ["5:10", "5:05", "4:40", "4:35", "4:38", "4:42", "5:20", "5:30"]
    seconds = [be._pace_str_to_seconds(s) for s in splits]
    results = be.find_best_efforts(splits, target_distances_km=(5,))

    brute_force_best = min(sum(seconds[i:i + 5]) for i in range(len(seconds) - 5 + 1))
    assert results[5].time_seconds == brute_force_best


def test_omits_a_distance_the_run_did_not_reach():
    # an 8km run has no valid 10K window -- must not fabricate one from a
    # partial/short window
    splits = ["5:00"] * 8
    results = be.find_best_efforts(splits, target_distances_km=(1, 5, 10))
    assert 10 not in results
    assert 5 in results
    assert 1 in results


def test_returns_empty_dict_for_no_splits():
    assert be.find_best_efforts([]) == {}


def test_accepts_raw_seconds_as_well_as_pace_strings():
    # some callers might already have seconds rather than "M:SS" strings
    splits_as_seconds = [300, 290, 280, 310, 305]
    results = be.find_best_efforts(splits_as_seconds, target_distances_km=(1,))
    assert results[1].time_seconds == 280


def test_exact_distance_equal_to_total_run_length_uses_the_whole_run():
    splits = ["5:00", "4:50", "5:10"]
    results = be.find_best_efforts(splits, target_distances_km=(3,))
    assert results[3].start_km == 0
    assert results[3].time_seconds == sum(be._pace_str_to_seconds(s) for s in splits)


def test_pace_seconds_per_km_is_time_divided_by_distance():
    splits = ["4:00"] * 5  # perfectly even effort
    results = be.find_best_efforts(splits, target_distances_km=(5,))
    assert results[5].pace_seconds_per_km == 240  # same as a single km, since it's even


# ---------- format_seconds_as_clock ----------

@pytest.mark.parametrize("seconds,expected", [
    (413, "6:53"),
    (60, "1:00"),
    (59, "0:59"),
    (3725, "1:02:05"),
    (0, "0:00"),
])
def test_format_seconds_as_clock(seconds, expected):
    assert be.format_seconds_as_clock(seconds) == expected
