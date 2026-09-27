"""
Best Efforts: the fastest N-kilometer stretch within a single run.

Strava's own "Best Efforts" uses a continuous GPS+time stream. This app
only stores the summary polyline (positions, no per-point timestamps), so
this works at the same granularity the pace chart already uses: one time
value per completed kilometer (see calculate_pace_dynamics in
activity_utils.py). A "5K best effort" here means the fastest 5 consecutive
kilometer-splits within the run, found with a sliding window -- not a
true continuous scan, but real data, not invented data.
"""
from dataclasses import dataclass


# Standard target distances (in whole kilometers) Best Efforts checks for.
# Half/full marathon distances aren't whole km numbers and this module only
# works at 1km granularity, so they're intentionally left out.
DEFAULT_TARGET_DISTANCES_KM = (1, 5, 10)


@dataclass
class BestEffort:
    distance_km: int
    time_seconds: float
    start_km: int          # 0-indexed: which split the window starts at
    pace_seconds_per_km: float


def _pace_str_to_seconds(pace_str):
    """Parses "M:SS" (e.g. "5:03") into whole seconds. Kilometer splits are
    always well under an hour, so this doesn't need to handle "H:MM:SS"."""
    minutes_str, seconds_str = pace_str.split(":")
    return int(minutes_str) * 60 + int(seconds_str)


def find_best_efforts(km_splits, target_distances_km=DEFAULT_TARGET_DISTANCES_KM):
    """km_splits: the per-kilometer splits for one run, in order, either as
    "M:SS" strings (what calculate_pace_dynamics returns) or as numbers of
    seconds. Returns {distance_km: BestEffort}, only for distances the run
    was actually long enough to cover -- a run under 5km has no 5K entry,
    rather than a misleading one built from a partial window.
    """
    if not km_splits:
        return {}

    seconds_per_km = [
        _pace_str_to_seconds(s) if isinstance(s, str) else float(s)
        for s in km_splits
    ]
    total_km = len(seconds_per_km)

    results = {}
    for distance_km in target_distances_km:
        if distance_km <= 0 or distance_km > total_km:
            continue

        # sliding window: running sum of `distance_km` consecutive splits,
        # updated in O(1) per step rather than re-summing each window
        window_sum = sum(seconds_per_km[:distance_km])
        best_sum = window_sum
        best_start = 0

        for start in range(1, total_km - distance_km + 1):
            window_sum += seconds_per_km[start + distance_km - 1] - seconds_per_km[start - 1]
            if window_sum < best_sum:
                best_sum = window_sum
                best_start = start

        results[distance_km] = BestEffort(
            distance_km=distance_km,
            time_seconds=best_sum,
            start_km=best_start,
            pace_seconds_per_km=best_sum / distance_km,
        )

    return results


def format_seconds_as_clock(total_seconds):
    """413 -> "6:53", 3725 -> "1:02:05" -- for displaying a best-effort time."""
    total_seconds = int(round(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"
