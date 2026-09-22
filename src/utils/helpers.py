import re
from flask import session, redirect, url_for
from src.api_methods.authorize import get_strava_authorization_url
from src.db.database_models import StravaToken
from datetime import datetime, time

def password_validation(password):
    pattern = pattern = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@#$%^&+=!]).{8,}$"

    if re.match(pattern, password):
        return True
    else:
        return False

def is_token_valid(session, user_id):
    strava_token = session.query(StravaToken).filter_by(user_id=user_id).first()
    if strava_token:
        return strava_token.expires_at > datetime.utcnow()
    return False

def handle_back_to_panel(session_db, user_id, client_id, redirect_uri):
    if is_token_valid(session_db, user_id):
        return redirect(url_for('token.exchange_token'))
    else:
        auth_url = get_strava_authorization_url(client_id, redirect_uri)
        session['auth_url'] = auth_url
        return redirect(auth_url)

def calculate_pace(moving_time, distance_km):
    if distance_km == 0: 
        return "N/A"
    pace_seconds = moving_time / distance_km  
    minutes = int(pace_seconds // 60)  
    seconds = int(pace_seconds % 60)  
    return f"{minutes}:{seconds:02} min/km"

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remainder_seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{remainder_seconds:02}"


def time_to_seconds(time_str):
    try:
        hours, minutes, seconds = map(int, time_str.split(":"))
        return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        return 0  
    
def take_the_seconds(time_str):
    current_value = datetime.strptime(time_str, "%H:%M:%S").time()
    return current_value.minute * 60 + current_value.second

def seconds_to_hms(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def calculate_pace(moving_time, distance_km):
    if distance_km == 0:
        return "N/A"  
    pace_seconds = moving_time / distance_km
    minutes = int(pace_seconds // 60)
    seconds = int(pace_seconds % 60)
    return f"{minutes:02}:{seconds:02} min/km"

def calculate_vo2_max(total_distance, moving_time, elevation_gain):
    velocity = (total_distance / moving_time) * 60  
    slope = elevation_gain / total_distance  
    vo2_max = (0.2 * velocity) + (0.9 * velocity * slope) + 3.5
    return vo2_max

def format_pace(seconds):
    minutes = int(seconds // 60)
    remainder_seconds = int(seconds % 60)
    return f"{minutes}:{remainder_seconds:02}"

