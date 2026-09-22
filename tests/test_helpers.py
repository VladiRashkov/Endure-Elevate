"""
Tests for src/utils/helpers.py.

NOTE on calculate_pace: this function is defined TWICE in the source file.
Python keeps only the second definition -- the first is dead code and never
runs. These tests check the definition that's actually active.
"""
import pytest

from src.utils import helpers


# ---------- calculate_pace ----------

def test_calculate_pace_formats_minutes_and_seconds_zero_padded():
    # 5:05/km — moving_time in seconds, distance in km
    assert helpers.calculate_pace(305, 1) == "05:05 min/km"


def test_calculate_pace_pads_single_digit_minutes():
    assert helpers.calculate_pace(65, 1) == "01:05 min/km"


def test_calculate_pace_returns_na_for_zero_distance():
    # guards the division; without this check, moving_time / 0 would crash
    assert helpers.calculate_pace(600, 0) == "N/A"


def test_calculate_pace_handles_a_fast_sub_minute_pace():
    assert helpers.calculate_pace(45, 1) == "00:45 min/km"


# ---------- format_time / seconds_to_hms ----------
# these two functions do exactly the same thing under different names --
# worth deduplicating, but until then both need to stay correct.

@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00:00"),
    (59, "00:00:59"),
    (60, "00:01:00"),
    (3725, "01:02:05"),
    (86399, "23:59:59"),
])
def test_format_time(seconds, expected):
    assert helpers.format_time(seconds) == expected


@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00:00"),
    (3725, "01:02:05"),
])
def test_seconds_to_hms(seconds, expected):
    assert helpers.seconds_to_hms(seconds) == expected


def test_format_time_and_seconds_to_hms_agree():
    # if these two ever drift apart, something got fixed in one place
    # and not the other
    for s in (0, 61, 3725, 7384):
        assert helpers.format_time(s) == helpers.seconds_to_hms(s)


# ---------- time_to_seconds ----------

def test_time_to_seconds_converts_hms_string():
    assert helpers.time_to_seconds("01:02:05") == 3725


def test_time_to_seconds_returns_zero_on_malformed_input():
    # the function swallows ValueError and returns 0 -- this documents
    # that on purpose, not as a hidden crash
    assert helpers.time_to_seconds("not a time") == 0


# ---------- take_the_seconds ----------

def test_take_the_seconds_reads_minutes_and_seconds():
    assert helpers.take_the_seconds("00:04:58") == 298  # 4*60 + 58


@pytest.mark.xfail(
    reason="BUG: take_the_seconds silently drops the hour component. "
           "A pace of 1:04:58 (e.g. a slow hiking pace over 60 min/km) "
           "returns the same 298 seconds as 0:04:58, instead of 3898. "
           "Found by writing this test -- worth fixing in helpers.py "
           "(use time_to_seconds instead, which handles hours correctly)."
)
def test_take_the_seconds_should_include_the_hour_component():
    assert helpers.take_the_seconds("01:04:58") == 3898  # 3600 + 4*60 + 58


# ---------- calculate_vo2_max ----------

def test_calculate_vo2_max_returns_a_plausible_value():
    # 10km in 3000s (30:00, 5:00/km pace), 50m elevation gain
    vo2 = helpers.calculate_vo2_max(total_distance=10000, moving_time=3000, elevation_gain=50)
    assert 30 < vo2 < 60  # sane range for a recreational runner


def test_calculate_vo2_max_increases_with_faster_pace():
    slow = helpers.calculate_vo2_max(10000, 4000, 50)   # 40:00 for 10km
    fast = helpers.calculate_vo2_max(10000, 2000, 50)   # 20:00 for 10km
    assert fast > slow


@pytest.mark.xfail(
    reason="BUG: calculate_vo2_max divides by total_distance for the slope "
           "term with no zero check. An activity with 0m recorded distance "
           "(a data glitch, or a manually logged non-GPS activity) crashes "
           "the whole page instead of showing a sensible result."
)
def test_calculate_vo2_max_should_not_crash_on_zero_distance():
    helpers.calculate_vo2_max(total_distance=0, moving_time=600, elevation_gain=10)


# ---------- format_pace ----------

def test_format_pace_formats_seconds_as_minutes_seconds():
    assert helpers.format_pace(303) == "5:03"


def test_format_pace_does_not_zero_pad_minutes():
    # unlike calculate_pace, this one does NOT zero-pad the minute -- documenting
    # the actual (inconsistent) behavior rather than assuming it matches calculate_pace
    assert helpers.format_pace(65) == "1:05"


# ---------- password_validation ----------

@pytest.mark.parametrize("password", [
    "Str0ng!Pass",
    "Another#1Ok",
    "P@ssw0rd123",
])
def test_password_validation_accepts_strong_passwords(password):
    assert helpers.password_validation(password) is True


@pytest.mark.parametrize("password,reason", [
    ("short1!", "under 8 characters"),
    ("nouppercase1!", "no uppercase letter"),
    ("NOLOWERCASE1!", "no lowercase letter"),
    ("NoDigitsHere!", "no digit"),
    ("NoSpecial123", "no special character"),
])
def test_password_validation_rejects_weak_passwords(password, reason):
    assert helpers.password_validation(password) is False, f"should reject: {reason}"
