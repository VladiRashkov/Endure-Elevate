# src/routers/token.py

from flask import Blueprint, redirect, request, session, render_template, flash, url_for
from src.api_methods.authorize import get_access_token, access_activity_data
from src.services.token_services import save_strava_tokens, get_token_logged_user
from sqlalchemy.orm import sessionmaker
from src.db.database_models import engine, StravaToken
from src.data_preprocessing.preprocess import preprocess_data
from src.services.activity_services import fetch_and_preprocess_activities, get_recent_activity
from src.utils.helpers import handle_back_to_panel, format_time
from datetime import datetime
SessionLocal = sessionmaker(bind=engine)
token_routes = Blueprint('token', __name__)


@token_routes.route('/callback/exchange_token')
def exchange_token():

    if 'user_id' not in session:
        return redirect('/user/login')

    user_id = session['user_id']
    client_id = "153633"
    client_secret = "f489beda3fa251ed10ee31915e710800c3c32ab8"
    code = request.args.get('code')

    session_db = SessionLocal()
    try:
        try:
            tokens = get_access_token(client_id, client_secret, code)
            save_strava_tokens(
                session=session_db,
                user_id=user_id,
                access_token=tokens['access_token'],
                refresh_token=tokens['refresh_token'],
                expires_at=tokens['expires_at']
            )
            access_token = tokens['access_token']
        except Exception:
            print("Token already exists. Fetching the existing access token.")
            existing_token = session_db.query(
                StravaToken).filter_by(user_id=user_id).first()
            if existing_token and existing_token.expires_at > datetime.utcnow():
                access_token = existing_token.access_token  # Use existing valid token
            else:
                return render_template('error.html', message="Failed to retrieve valid access token.")
        
        fetch_and_preprocess_activities(access_token, user_id)

        recent_activity = get_recent_activity(session_db, user_id)

        if recent_activity:
            return render_template('second_window.html', recent_activity_id=recent_activity.id)
        else:
            return render_template('second_window.html', recent_activity_id=None)

    except Exception as e:
        print(f"Error: {e}")
        return render_template('error.html', message="Failed to fetch activities.")
    finally:
        session_db.close()


@token_routes.route('/all_time_runs')
def all_time_runs():
    if 'user_id' not in session:
        return redirect('/user/login')

    user_id = session['user_id']
    session_db = SessionLocal()

    strava_token = get_token_logged_user(session_db, user_id)

    if not strava_token or not strava_token.access_token:
        return render_template("error.html", message="Access token not found. Please authenticate with Strava again.")

    access_token = strava_token.access_token
    if not access_token:
        return render_template("error.html", message="Access token is missing.")

    try:
        df = fetch_and_preprocess_activities(access_token, user_id)

        if not df.empty:
            columns_needed = [
                "id", "name", "type", "distance", "moving_time",
                "total_elevation_gain", "start_date", "average_heartrate"
            ]
            extracted_data = df[columns_needed].copy()
            pace_in_seconds = (
                extracted_data['moving_time'] / (extracted_data['distance'] / 1000))
            extracted_data['pace'] = pace_in_seconds.apply(
                lambda x: f"{int(x // 60)}:{int(x % 60):02d} min/km"
            )

            extracted_data['distance'] = (
                (extracted_data['distance'] / 1000).round(3)).astype(str) + " km"

            extracted_data['start_date'] = extracted_data['start_date'].str.replace(
                'T', ' ').str.replace('Z', '')

            extracted_data['total_elevation_gain'] = extracted_data['total_elevation_gain'].astype(
                str) + " m"

            extracted_data['moving_time'] = extracted_data['moving_time'].apply(
                format_time)

            extracted_data['average_heartrate'] = extracted_data['average_heartrate'].astype(
                str) + " BPM"

            return render_template(
                'results.html',
                headers=extracted_data.columns.tolist(),
                rows=extracted_data.values.tolist()
            )
        else:
            return render_template("error.html", message="No running activities found.")
    except Exception as e:
        print(f"Error fetching activities: {e}")
        return render_template("error.html", message="Failed to fetch running activities.")


@token_routes.route('/back_to_panel')
def back_to_panel():
    user_id = session.get('user_id')
    if not user_id:
        flash("User not logged in. Please log in.")
        return redirect(url_for('user.login'))

    client_id = "153633"
    redirect_uri = url_for('token.exchange_token', _external=True)

    session_db = SessionLocal()
    try:
        return handle_back_to_panel(session_db, user_id, client_id, redirect_uri)
    finally:
        session_db.close()
