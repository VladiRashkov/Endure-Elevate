"""
Training load: TRIMP (Training Impulse) and ACWR (Acute:Chronic Workload Ratio).

TRIMP estimates the physiological "cost" of a single run from its duration
and heart rate, weighting harder efforts non-linearly (a hard 20-minute
tempo run counts for more than a full 20-minute-equivalent easy jog).

ACWR compares a short-term "acute" load (last 7 days) against a long-term
"chronic" load (last 28 days, expressed as a weekly average) to flag when
someone is ramping up training volume faster than their body has adapted to
-- the single biggest modifiable risk factor for overuse running injuries.

References:
- Banister TRIMP: Banister, E.W. (1991), "Modeling elite athletic performance"
- ACWR risk bands: Gabbett, T.J. (2016), "The training-injury prevention
  paradox: should athletes be training smarter and harder?"
"""
import math
from dataclasses import dataclass
from datetime import datetime, timedelta


def _as_datetime(value):
    """Normalize a start_date that may be a real datetime or a string.

    The Activity table stores start_date as a plain String column, so every
    row comes back as str; some other call sites in this app already parse
    real datetimes elsewhere, so this stays permissive about both."""
    if isinstance(value, datetime):
        return value
    v = value.rstrip('Z').replace('T', ' ')
    return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')

# Banister's male exponential weighting constants. (A female-specific pair
# exists in the literature -- k=0.86, b=1.67 -- but we don't collect sex,
# so we use one constant set for everyone, same as most consumer apps do.)
_TRIMP_K = 0.64
_TRIMP_B = 1.92


def calculate_trimp(moving_time_seconds, average_heartrate, resting_hr, max_hr):
    """Banister TRIMP for a single run.

    Returns None (rather than raising) when heart-rate data is missing or
    the HR range is nonsensical, so callers can skip that run instead of
    crashing the whole calculation.
    """
    if moving_time_seconds is None or average_heartrate is None:
        return None
    if resting_hr is None or max_hr is None:
        return None
    if max_hr <= resting_hr or moving_time_seconds <= 0:
        return None

    duration_minutes = moving_time_seconds / 60
    relative_intensity = (average_heartrate - resting_hr) / (max_hr - resting_hr)
    # Clamp: a device glitch reporting avg HR below resting or above max
    # shouldn't produce a negative or explosive TRIMP.
    relative_intensity = max(0.0, min(1.0, relative_intensity))
    weighting = _TRIMP_K * math.exp(_TRIMP_B * relative_intensity)
    return duration_minutes * relative_intensity * weighting


@dataclass
class AcwrResult:
    acute_load: float          # sum of TRIMP over the last 7 days
    chronic_load: float        # last-28-days TRIMP total, expressed as a weekly average
    ratio: float                # acute / chronic
    band: str                   # "low" | "safe" | "caution" | "high"
    runs_used: int               # runs that had HR data and were included
    runs_skipped_no_hr: int       # runs in the 28-day window with no HR data


def _risk_band(ratio):
    # Gabbett 2016 "sweet spot" bands, the de facto standard cited by most
    # ACWR-in-practice writeups.
    if ratio < 0.8:
        return "low"        # undertraining relative to recent fitness
    if ratio <= 1.3:
        return "safe"
    if ratio <= 1.5:
        return "caution"
    return "high"


def calculate_acwr(activities, resting_hr, max_hr, as_of=None):
    """activities: iterable of objects with .start_date (datetime),
    .moving_time (seconds), .average_heartrate (bpm or None).

    Returns None when there isn't enough HR-tagged data in the 28-day
    window to say anything meaningful (rather than a misleading ratio).
    """
    as_of = as_of or datetime.utcnow()
    seven_days_ago = as_of - timedelta(days=7)
    twenty_eight_days_ago = as_of - timedelta(days=28)

    acute_total = 0.0
    chronic_total = 0.0
    runs_used = 0
    runs_skipped = 0

    for activity in activities:
        start = _as_datetime(activity.start_date)
        if start < twenty_eight_days_ago or start > as_of:
            continue

        trimp = calculate_trimp(
            activity.moving_time,
            getattr(activity, "average_heartrate", None),
            resting_hr,
            max_hr,
        )
        if trimp is None:
            runs_skipped += 1
            continue

        runs_used += 1
        chronic_total += trimp
        if start >= seven_days_ago:
            acute_total += trimp

    if runs_used == 0:
        return None

    chronic_weekly_equivalent = (chronic_total / 28) * 7
    if chronic_weekly_equivalent == 0:
        return None

    ratio = acute_total / chronic_weekly_equivalent
    return AcwrResult(
        acute_load=round(acute_total, 1),
        chronic_load=round(chronic_weekly_equivalent, 1),
        ratio=round(ratio, 2),
        band=_risk_band(ratio),
        runs_used=runs_used,
        runs_skipped_no_hr=runs_skipped,
    )