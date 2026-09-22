"""
Tests for the chart-generation functions in src/utils/activity_utils.py.

These are pure functions: numbers in, an SVG string out, no file writes,
no network calls. That makes them cheap and safe to test directly.
"""
import re

import pytest

from src.utils import activity_utils as au


# ---------- generate_elevation_chart ----------

def test_elevation_chart_shows_the_correct_gain():
    html = au.generate_elevation_chart(elevation_high=457.0, elevation_low=60.0)
    assert "397" in html  # 457 - 60


def test_elevation_chart_handles_zero_gain_without_crashing():
    html = au.generate_elevation_chart(elevation_high=100.0, elevation_low=100.0)
    assert "0" in html


def test_elevation_chart_returns_wrapped_svg():
    html = au.generate_elevation_chart(300.0, 50.0)
    assert "<svg" in html and "</svg>" in html


# ---------- generate_vo2_max_progress ----------

def test_vo2_max_chart_shows_the_value_to_one_decimal():
    html = au.generate_vo2_max_progress(45.3)
    assert "45.3" in html


def test_vo2_max_chart_handles_zero():
    html = au.generate_vo2_max_progress(0.0)
    assert "<svg" in html  # doesn't crash, still renders a ring


def test_vo2_max_chart_handles_a_value_over_the_display_max():
    # a value above max_limit shouldn't blow up the arc math
    html = au.generate_vo2_max_progress(90.0, max_limit=70)
    assert "<svg" in html


# ---------- generate_pace_chart ----------

def test_pace_chart_plots_one_point_per_kilometer():
    paces = ["5:03", "4:58", "5:10"]
    html = au.generate_pace_chart(paces)
    # one <circle> marker per km
    assert html.count("<circle") == len(paces)


def test_pace_chart_handles_a_single_kilometer():
    html = au.generate_pace_chart(["5:00"])
    assert "<svg" in html
    assert html.count("<circle") == 1


def test_pace_chart_formats_mmss_labels_not_raw_seconds():
    # a real chart shows "5:03", never the raw second count "303"
    html = au.generate_pace_chart(["5:03"])
    assert re.search(r"\b\d:\d\d\b", html)


# ---------- generate_heart_rate_chart ----------

def test_heart_rate_chart_shows_both_values():
    html = au.generate_heart_rate_chart(avg_hr=148, max_hr=176)
    assert "148" in html and "176" in html


def test_heart_rate_chart_has_no_external_script_dependency():
    # this replaced an old matplotlib/mpld3 version that silently failed
    # offline because it loaded d3.js from a CDN -- make sure that's gone.
    html = au.generate_heart_rate_chart(150, 180)
    assert "cdn" not in html.lower()
    assert "d3js.org" not in html
    assert "mpld3" not in html.lower()
