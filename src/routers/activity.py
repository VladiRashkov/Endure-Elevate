from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, jsonify
from sqlalchemy.orm import sessionmaker
from src.routers.token import db_session, login_required
from src.db.database_models import engine, Activity
from src.utils.activity_utils import create_map, \
generate_elevation_chart, generate_vo2_max_progress, generate_heart_rate_chart,\
    calculate_pace_dynamics, generate_pace_chart
from src.utils.helpers import seconds_to_hms, calculate_pace, \
    calculate_vo2_max, format_pace
from src.utils.training_load import calculate_acwr
from src.utils.best_efforts import find_best_efforts, format_seconds_as_clock
SessionLocal = sessionmaker(bind=engine)
activity_routes = Blueprint('activity', __name__)

def _as_datetime(value):
    """start_date may be a real datetime or a leftover plain string from
    older rows — normalize to datetime so callers can just use .year / .month
    without caring which."""
    if isinstance(value, datetime):
        return value
    v = value.rstrip('Z').replace('T', ' ')
    return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')

@activity_routes.route('/activities')
def view_activities():
    session_db = SessionLocal()
    try:
        user_id = session['user_id']
        activities = session_db.query(Activity).filter(Activity.user_id == user_id).all()
        return render_template('activities.html', activities=activities)
    finally:
        session_db.close()


@activity_routes.route('/daily_activity')
def default_activity():
    session_db = SessionLocal()
    user_id = session.get('user_id')
    try:
        if not user_id:
            return render_template("error.html", message="User not logged in.")
        
        most_recent_activity = (
            session_db.query(Activity)
            .filter(Activity.user_id == user_id)
            .order_by(Activity.start_date.desc())
            .first()
        )
        
        if most_recent_activity:
            return redirect(url_for('activity.daily_activity', activity_id=most_recent_activity.id))
        
        return render_template("error.html", message="No activities found.")
    finally:
        session_db.close()



@activity_routes.route('/daily_activity/<int:activity_id>')
def daily_activity(activity_id):
    session_db = SessionLocal()
    try:
        user_id = session.get('user_id')
        if not user_id:
            return render_template("error.html", message="User not logged in.")
        
        activity = (
            session_db.query(Activity)
            .filter(Activity.user_id == user_id, Activity.id == activity_id)
            .first()
        )
        def _as_datetime(value):
            """start_date can be a real datetime or a leftover string, depending on
            when the row was saved."""
            if isinstance(value, datetime):
                return value
            v = value.rstrip('Z').replace('T', ' ')
            return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
        if not activity:
            return render_template("error.html", message="Activity not found.")
        start_display = _as_datetime(activity.start_date).strftime('%d %b %Y, %H:%M')
        previous_activity = (
            session_db.query(Activity)
            .filter(Activity.user_id == user_id, Activity.id < activity_id)
            .order_by(Activity.id.desc())
            .first()
        )
        
        next_activity = (
            session_db.query(Activity)
            .filter(Activity.user_id == user_id, Activity.id > activity_id)
            .order_by(Activity.id.asc())
            .first()
        )
        
        summary_polyline = activity.polyline_data
        total_distance = activity.distance
        moving_time = activity.moving_time
        elevation_high = activity.elevation_high
        elevation_low = activity.elevation_low
        avg_hr = activity.average_heartrate
        max_hr = activity.max_heartrate
        calories = activity.calories
        avg_cadence = activity.average_cadence
        
        elevation_gain = elevation_high - elevation_low
        vo2_max = calculate_vo2_max(total_distance, moving_time, elevation_gain)
        paces = calculate_pace_dynamics(summary_polyline, total_distance, moving_time)
        avg_pace_seconds = sum([int(p.split(':')[0]) * 60 + int(p.split(':')[1]) for p in paces]) // len(paces)
        avg_pace = format_pace(avg_pace_seconds)
        
        pace_chart_html = generate_pace_chart(paces)
        elevation_chart_html = generate_elevation_chart(elevation_high, elevation_low)
        hr_chart_html = generate_heart_rate_chart(avg_hr, max_hr)
        vo2_max_chart_html = generate_vo2_max_progress(vo2_max)
        map_path = create_map(activity.id, summary_polyline, avg_pace, elevation_gain, vo2_max, avg_hr, calories, avg_cadence)
        print(f"Map Path: {map_path}")
        
        return render_template(
            "daily_activity.html",
            map_path=map_path,
            pace_chart=pace_chart_html,
            elevation_chart=elevation_chart_html,
            hr_chart=hr_chart_html,
            vo2_max_chart=vo2_max_chart_html,
            current_activity=activity,
            previous_activity=previous_activity,
            next_activity=next_activity,
            start_display=start_display,
        )
    finally:
        session_db.close()


@activity_routes.route('/get-progress', methods=['GET'])
def get_progress():
    session_db = SessionLocal()
    try:
        user_id = session.get('user_id')

        last_three_runs = (
            session_db.query(Activity)
            .filter(Activity.type == 'Run', Activity.user_id == user_id)
            .order_by(Activity.start_date.desc())
            .limit(3)
            .all()
        )
        last_three_data = [
            {
                "name": run.name,
                "date": run.start_date,
                "distance_km": f"{run.distance / 1000:.2f} km",
                "time_taken": seconds_to_hms(run.moving_time),
                "pace": calculate_pace(run.moving_time, run.distance / 1000)
            } for run in last_three_runs
        ]

        latest_activity = (
            session_db.query(Activity)
            .filter(Activity.type == 'Run', Activity.user_id == user_id)
            .order_by(Activity.start_date.desc())
            .first()
        )
        if not latest_activity:
            return render_template(
                'progress.html', last_three_runs=[], monthly_progress=[],
                total_distance="0.00 km", latest_year=None,
            )

        latest_year = _as_datetime(latest_activity.start_date).year          # <-- patched

        monthly_data = (
            session_db.query(Activity)
            .filter(
                Activity.type == 'Run',
                Activity.user_id == user_id,
                Activity.start_date >= datetime(latest_year, 1, 1),
                Activity.start_date < datetime(latest_year + 1, 1, 1),
            )
            .all()
        )

        monthly_progress = {}
        for activity in monthly_data:
            month = _as_datetime(activity.start_date).month                  # <-- patched
            monthly_progress[month] = monthly_progress.get(month, 0) + activity.distance / 1000

        monthly_progress_data = [
            {"month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month - 1],
             "distance_km": f"{distance:.2f} km"}
            for month, distance in sorted(monthly_progress.items())
        ]

        total_year_distance = sum(monthly_progress.values())

        return render_template(
            'progress.html',
            last_three_runs=last_three_data,
            monthly_progress=monthly_progress_data,
            total_distance=f"{total_year_distance:.2f} km",
            latest_year=latest_year,
        )
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        session_db.close()

@activity_routes.route("/training-load")
@login_required
def training_load():
    user_id = session['user_id']
    with db_session() as db:
        activities = db.query(Activity).filter(Activity.user_id == user_id).all()
        resting_hr, max_hr = 50, 190  # placeholder until sourced properly
        acwr = calculate_acwr(activities, resting_hr, max_hr)
    return render_template("training_load.html", acwr=acwr)

@activity_routes.route("/best-efforts")
@login_required
def best_efforts():
    user_id = session['user_id']
    global_best = {}  # distance_km -> {time_seconds, activity_id, achieved_on}

    with db_session() as db:
        activities = db.query(Activity).filter(Activity.user_id == user_id).all()
        for activity in activities:
            if not activity.polyline_data:
                continue
            paces = calculate_pace_dynamics(activity.polyline_data, activity.distance, activity.moving_time)
            for distance_km, effort in find_best_efforts(paces).items():
                current_best = global_best.get(distance_km)
                if current_best is None or effort.time_seconds < current_best["time_seconds"]:
                    global_best[distance_km] = {
                        "time_seconds": effort.time_seconds,
                        "activity_id": activity.id,
                        "achieved_on": _as_datetime(activity.start_date).strftime("%d %b %Y"),
                    }

    bests = []
    for distance_km in (1, 5, 10):
        best = global_best.get(distance_km)
        if best:
            bests.append({
                "distance_km": distance_km,
                "reached": True,
                "time_display": format_seconds_as_clock(best["time_seconds"]),
                "pace_display": format_seconds_as_clock(best["time_seconds"] / distance_km),
                "activity_id": best["activity_id"],
                "achieved_on": best["achieved_on"],
            })
        else:
            bests.append({"distance_km": distance_km, "reached": False})

    return render_template("best_efforts.html", bests=bests)