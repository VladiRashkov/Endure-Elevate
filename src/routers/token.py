# src/routers/token.py
import logging
import os
from contextlib import contextmanager
from functools import wraps

import pandas as pd
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy.orm import sessionmaker

from src.api_methods.authorize import get_access_token
from src.db.database_models import Activity, engine
from src.services.activity_services import fetch_and_preprocess_activities
from src.services.token_services import get_token_logged_user, get_valid_access_token, save_strava_tokens
from src.utils.helpers import format_time

logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(bind=engine)
token_routes = Blueprint('token', __name__)

STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID', '153633')      # public, safe to keep
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')        # secret: environment / .env only
if not STRAVA_CLIENT_SECRET:
    logger.warning('STRAVA_CLIENT_SECRET is not set; Strava token exchange and refresh will fail.')

RUN_COLUMNS = [
    'id', 'name', 'type', 'distance', 'moving_time',
    'total_elevation_gain', 'start_date', 'average_heartrate',
]


# ---------- helpers ----------

@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash('User not logged in. Please log in.')
            return redirect(url_for('user.login'))
        return view(*args, **kwargs)
    return wrapped


def _format_pace(moving_time, distance_m):
    if pd.isna(distance_m) or not distance_m:
        return '–'
    seconds = moving_time / (distance_m / 1000)
    return f'{int(seconds // 60)}:{int(seconds % 60):02d} min/km'


def _get_recent_activity_from_db(db, user_id):
    """Read-only: most recent stored run. Does NOT call Strava."""
    return (
        db.query(Activity)
        .filter(Activity.user_id == user_id)
        .order_by(Activity.start_date.desc())
        .first()
    )


def _activities_to_df(activities):
    """Turn stored Activity rows into the same shape _build_runs_table expects
    (as if it had just come back from Strava): start_date as a 'T...Z' string,
    distance/moving_time as raw numbers.

    start_date may be a real datetime (current save path) or a leftover plain
    string from older rows / an earlier version of the sync code -- handle both
    rather than assuming every row was written the same way."""
    rows = []
    for a in activities:
        if isinstance(a.start_date, str):
            start_date_str = a.start_date if a.start_date.endswith('Z') else a.start_date + 'Z'
            if 'T' not in start_date_str:
                start_date_str = start_date_str.replace(' ', 'T', 1)
        else:
            start_date_str = a.start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        rows.append({
            'id': a.id,
            'name': a.name,
            'type': a.type,
            'distance': a.distance,
            'moving_time': a.moving_time,
            'total_elevation_gain': a.total_elevation_gain,
            'start_date': start_date_str,
            'average_heartrate': a.average_heartrate,
        })
    return pd.DataFrame(rows, columns=RUN_COLUMNS)


def _build_runs_table(df):
    data = df.reindex(columns=RUN_COLUMNS).copy()   # a missing column becomes empty instead of a KeyError
    data['pace'] = [_format_pace(t, d) for t, d in zip(data['moving_time'], data['distance'])]
    data['distance'] = (data['distance'] / 1000).round(3).astype(str) + ' km'
    data['start_date'] = data['start_date'].str.replace('T', ' ').str.replace('Z', '')
    data['total_elevation_gain'] = data['total_elevation_gain'].astype(str) + ' m'
    data['moving_time'] = data['moving_time'].apply(format_time)
    data['average_heartrate'] = data['average_heartrate'].apply(
        lambda v: f'{v:.0f} BPM' if pd.notna(v) else '–'
    )
    return data.columns.tolist(), data.values.tolist()


# ---------- routes ----------

@token_routes.route('/callback/exchange_token')
@login_required
def exchange_token():
    """OAuth callback ONLY: trade Strava's one-time code for tokens, sync once, then go to the panel."""
    user_id = session['user_id']

    if request.args.get('error'):
        return render_template('error.html', message='Strava authorization was cancelled or denied.')

    code = request.args.get('code')
    if not code:
        return redirect(url_for('token.back_to_panel'))

    with db_session() as db:
        try:
            tokens = get_access_token(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, code)
            save_strava_tokens(
                session=db,
                user_id=user_id,
                access_token=tokens['access_token'],
                refresh_token=tokens['refresh_token'],
                expires_at=tokens['expires_at'],
            )
            access_token = tokens['access_token']
        except Exception:
            logger.warning('Strava code exchange failed.', exc_info=True)
            if get_token_logged_user(db, user_id) is None:
                return render_template('error.html', message='Strava rejected the authorization. Please try again.')
            access_token = None

        # The ONLY place a full Strava sync happens automatically: right after authorizing.
        if access_token:
            try:
                fetch_and_preprocess_activities(access_token, user_id)
            except Exception:
                logger.exception('Initial activity sync failed after authorization')

    return redirect(url_for('token.back_to_panel'))


@token_routes.route('/sync')
@login_required
def sync_now():
    """Explicit 'Sync now' action — link/button this from the UI when the user wants fresh data."""
    user_id = session['user_id']
    with db_session() as db:
        try:
            access_token = get_valid_access_token(db, user_id, STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET)
        except Exception:
            logger.exception('Could not refresh the Strava token during sync')
            access_token = None

        if access_token is None:
            return redirect(url_for('user.strava_login'))

        try:
            fetch_and_preprocess_activities(access_token, user_id)
        except Exception:
            logger.exception('Manual sync failed')
            flash('Could not sync with Strava right now. Please try again.')

    return redirect(url_for('token.back_to_panel'))


@token_routes.route('/back_to_panel')
@login_required
def back_to_panel():
    """The main panel: reads from the database. Does NOT call Strava."""
    user_id = session['user_id']

    with db_session() as db:
        recent_activity = _get_recent_activity_from_db(db, user_id)

        return render_template(
            'second_window.html',
            recent_activity_id=recent_activity.id if recent_activity else None,
        )


@token_routes.route('/all_time_runs')
@login_required
def all_time_runs():
    """Reads from the database. Does NOT call Strava."""
    user_id = session['user_id']

    with db_session() as db:
        activities = (
            db.query(Activity)
            .filter(Activity.user_id == user_id)
            .order_by(Activity.start_date.desc())
            .all()
        )

    if not activities:
        return render_template("error.html", message="No running activities found. Try syncing with Strava.")

    df = _activities_to_df(activities)
    headers, rows = _build_runs_table(df)
    return render_template('results.html', headers=headers, rows=rows)