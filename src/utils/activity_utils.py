import os

import folium
import polyline
from geopy.distance import geodesic
import math

from src.utils.helpers import format_pace



def generate_heart_rate_chart(avg_hr, max_hr):
    W, H = 340, 220
    pad_l, pad_b, pad_t = 60, 40, 20
    plot_h = H - pad_t - pad_b
    hi = max(max_hr * 1.15, 1)

    bars = [("Average", avg_hr, BRAND), ("Max", max_hr, BRAND_DEEP)]
    bar_w = 90
    gap = 60
    total_w = bar_w * 2 + gap
    x0 = (W - total_w) / 2

    parts = [f'<line x1="{pad_l-10}" y1="{H-pad_b}" x2="{W-10}" y2="{H-pad_b}" stroke="{LINE}" stroke-width="1.5"/>']
    for i, (label, value, color) in enumerate(bars):
        x = x0 + i * (bar_w + gap)
        bar_h = plot_h * (value / hi)
        y = (H - pad_b) - bar_h
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="8" fill="{color}"/>'
            f'<text x="{x + bar_w/2:.1f}" y="{y - 10:.1f}" fill="{INK}" font-size="20" font-weight="700" '
            f'font-family="{FONT_DISPLAY}" text-anchor="middle">{value:.0f}</text>'
            f'<text x="{x + bar_w/2:.1f}" y="{H - pad_b + 22:.1f}" fill="{MUTED}" font-size="13" text-anchor="middle">{label}</text>'
        )
    parts.append(f'<text x="{pad_l-10}" y="16" fill="{MUTED}" font-size="12">BPM</text>')
    return _wrap("".join(parts), W, H)


def calculate_pace_dynamics(polyline_data, total_distance, total_time):
    coordinates = polyline.decode(polyline_data)
    paces = []
    distance_covered = 0
    time_covered = 0
    km_distance = 1000

    for i in range(len(coordinates) - 1):
        start, end = coordinates[i], coordinates[i + 1]
        segment_distance = geodesic(start, end).meters
        segment_time = total_time * (segment_distance / total_distance)
        distance_covered += segment_distance
        time_covered += segment_time

        if distance_covered >= km_distance:
            minutes = int(time_covered // 60)
            seconds = int(time_covered % 60)
            paces.append(f"{minutes}:{seconds:02d}")
            distance_covered -= km_distance
            time_covered = 0

    if distance_covered > 0:
        minutes = int(time_covered // 60)
        seconds = int(time_covered % 60)
        paces.append(f"{minutes}:{seconds:02d}")

    return paces


def create_map(activity_id, polyline_data, avg_pace, avg_gain, vo2_max, avg_hr, calories, avg_cadence):
    """Renders once per activity and reuses the file on later views.

    A past run's data never changes, so once its map exists on disk there's
    no need to decode the polyline and rebuild the Leaflet map again — we
    just point back at the same file. Delete the file (or bump SCHEMA_VERSION
    below) if you ever change what this map renders and need old ones rebuilt.
    """
    map_dir = "static/maps"
    os.makedirs(map_dir, exist_ok=True)
    SCHEMA_VERSION = 1
    map_path = os.path.join(map_dir, f"route_map_{activity_id}_v{SCHEMA_VERSION}.html")

    if not os.path.exists(map_path):
        coordinates = polyline.decode(polyline_data)
        start_point = coordinates[0]
        info_point = coordinates[100] if len(coordinates) > 100 else coordinates[-1]
        route_map = folium.Map(location=start_point, zoom_start=14)

        folium.PolyLine(locations=coordinates, color='blue', weight=5).add_to(route_map)
        folium.Marker(location=start_point, popup="Start", icon=folium.Icon(color="green")).add_to(route_map)
        folium.Marker(location=coordinates[-1], popup="End", icon=folium.Icon(color="red")).add_to(route_map)

        summary_html = f"""
        <div style="font-size:14px;">
            <b>Workout Summary</b><br>
            Avg Pace: {avg_pace} min/km<br>
            Elevation Gain: {avg_gain} m<br>
            VO2 Max: {vo2_max:.2f} mL/kg/min<br>
            Avg HR: {avg_hr} bpm<br>
            Calories: {calories} kcal<br>
            Avg Cadence: {avg_cadence} spm<br>
        </div>
        """
        folium.Marker(
            location=info_point,
            popup=folium.Popup(summary_html, max_width=250),
            icon=folium.Icon(icon="info-sign", color="blue"),
        ).add_to(route_map)

        route_map.save(map_path)

    return map_path.replace('\\', '/').replace("static/", "/static/")


import math

BRAND = "#0b5c7e"
BRAND_DEEP = "#073b52"
TINT = "#e4eff4"
INK = "#12262f"
MUTED = "#55707c"
LINE = "#cfdde3"
FONT = "'Figtree','Segoe UI',system-ui,sans-serif"
FONT_DISPLAY = "'Bricolage Grotesque','Segoe UI',system-ui,sans-serif"


def _wrap(svg, width, height):
    return (
        f'<div style="width:100%;overflow-x:auto;">'
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;font-family:{FONT};" '
        f'xmlns="http://www.w3.org/2000/svg">{svg}</svg></div>'
    )


def generate_elevation_chart(elevation_high, elevation_low):
    gain = elevation_high - elevation_low
    W, H = 560, 170
    x0, x1 = 50, W - 50
    y_base = 120

    # relative rise of the "high" marker vs "low" marker, purely for the little
    # incline line -- capped so a huge gain doesn't fly off the top
    rise = min(60, 20 + gain / 10)
    y_low, y_high = y_base, y_base - rise

    svg = f'''
    <line x1="{x0}" y1="{y_base}" x2="{x1}" y2="{y_base}" stroke="{LINE}" stroke-width="1.5"/>
    <path d="M{x0},{y_low} L{x1},{y_high}" stroke="{BRAND}" stroke-width="3" fill="none" stroke-linecap="round"/>
    <circle cx="{x0}" cy="{y_low}" r="5" fill="{BRAND_DEEP}"/>
    <circle cx="{x1}" cy="{y_high}" r="5" fill="{BRAND_DEEP}"/>
    <text x="{x0}" y="{y_base + 22}" fill="{MUTED}" font-size="13" text-anchor="middle">Low</text>
    <text x="{x0}" y="{y_low - 12}" fill="{INK}" font-size="13" font-weight="600" text-anchor="middle">{elevation_low:.0f} m</text>
    <text x="{x1}" y="{y_base + 22}" fill="{MUTED}" font-size="13" text-anchor="middle">High</text>
    <text x="{x1}" y="{y_high - 12}" fill="{INK}" font-size="13" font-weight="600" text-anchor="middle">{elevation_high:.0f} m</text>
    <text x="{W/2}" y="34" fill="{INK}" font-size="30" font-weight="700" font-family="{FONT_DISPLAY}" text-anchor="middle">{gain:.0f}<tspan font-size="16" font-weight="500" fill="{MUTED}"> m gain</tspan></text>
    '''
    return _wrap(svg, W, H)


def generate_vo2_max_progress(vo2_max, max_limit=70):
    W, H = 260, 260
    cx, cy, r = W/2, H/2, 95
    stroke = 18
    pct = max(0, min(1, vo2_max / max_limit))
    circumference = 2 * math.pi * r
    start_angle = -90

    def arc_path(pct_val):
        if pct_val <= 0:
            return ""
        end_angle = start_angle + 360 * pct_val
        large_arc = 1 if pct_val > 0.5 else 0
        x1 = cx + r * math.cos(math.radians(start_angle))
        y1 = cy + r * math.sin(math.radians(start_angle))
        x2 = cx + r * math.cos(math.radians(end_angle))
        y2 = cy + r * math.sin(math.radians(end_angle))
        return f'M{x1:.2f},{y1:.2f} A{r},{r} 0 {large_arc} 1 {x2:.2f},{y2:.2f}'

    svg = f'''
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TINT}" stroke-width="{stroke}"/>
    <path d="{arc_path(pct)}" fill="none" stroke="{BRAND}" stroke-width="{stroke}" stroke-linecap="round"/>
    <text x="{cx}" y="{cy - 4}" fill="{INK}" font-size="34" font-weight="700" font-family="{FONT_DISPLAY}" text-anchor="middle">{vo2_max:.1f}</text>
    <text x="{cx}" y="{cy + 22}" fill="{MUTED}" font-size="13" text-anchor="middle">mL/kg/min</text>
    '''
    return _wrap(svg, W, H)


def generate_pace_chart(paces):
    paces_sec = [int(p.split(':')[0]) * 60 + int(p.split(':')[1]) for p in paces]
    n = len(paces_sec)
    W = max(420, 70 * n + 80)
    H = 260
    pad_l, pad_r, pad_t, pad_b = 55, 25, 20, 36
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b

    lo, hi = min(paces_sec), max(paces_sec)
    if lo == hi:
        lo -= 30
        hi += 30
    pad_range = (hi - lo) * 0.15 or 10
    lo -= pad_range
    hi += pad_range

    def x_of(i):
        return pad_l + (plot_w * i / (n - 1) if n > 1 else plot_w / 2)

    def y_of(v):
        return pad_t + plot_h * (1 - (v - lo) / (hi - lo))

    def fmt(sec):
        sec = int(sec)
        return f"{sec // 60}:{sec % 60:02d}"

    grid_lines = []
    n_ticks = 4
    for k in range(n_ticks + 1):
        v = lo + (hi - lo) * k / n_ticks
        y = y_of(v)
        grid_lines.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{W - pad_r}" y2="{y:.1f}" stroke="{LINE}" stroke-width="1" stroke-dasharray="4,4"/>'
            f'<text x="{pad_l - 10}" y="{y + 4:.1f}" fill="{MUTED}" font-size="12" text-anchor="end">{fmt(v)}</text>'
        )

    points = [(x_of(i), y_of(s)) for i, s in enumerate(paces_sec)]
    path_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)

    dots = []
    for i, (x, y) in enumerate(points):
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#fff" stroke="{BRAND}" stroke-width="2.5">'
            f'<title>Km {i+1}: {fmt(paces_sec[i])} min/km</title></circle>'
            f'<text x="{x:.1f}" y="{H - 10}" fill="{MUTED}" font-size="12" text-anchor="middle">{i+1}</text>'
        )

    svg = f'''
    {"".join(grid_lines)}
    <path d="{path_d}" fill="none" stroke="{BRAND}" stroke-width="2.5" stroke-linejoin="round"/>
    {"".join(dots)}
    <text x="{pad_l}" y="14" fill="{MUTED}" font-size="12">min:sec / km</text>
    '''
    return _wrap(svg, W, H)