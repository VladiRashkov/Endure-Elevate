import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from src.services.user_services import get_user_by_email, create_user
from src.api_methods.authorize import get_strava_authorization_url
from src.utils.helpers import password_validation
from src.db.database_models import SessionLocal, StravaToken
from src.services.token_services import get_token_logged_user

user_routes = Blueprint('user', __name__)

STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID', '153633')  # the client id is public; the secret is not
PASSWORD_RULES = (
    'The password must contain at least 8 characters, 1 digit, '
    '1 capital letter, 1 small letter, and 1 special character.'
)


def _log_in(user):
    """Start a fresh session for this user. Used by both register and login."""
    session.clear()
    session['user_id'] = user.id
    session['email'] = user.email
    session['name'] = getattr(user, 'name', '') or ''


@user_routes.app_context_processor
def inject_user_name():
    """Makes {{ user_name }} available in every template without passing it from each route."""
    return {'user_name': session.get('name') or session.get('email', '')}


@user_routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if not password_validation(password):
            flash(PASSWORD_RULES)
            return redirect(url_for('user.register'))

        if get_user_by_email(email):
            flash('Email already exists. Please log in.')
            return redirect(url_for('user.login'))

        new_user = create_user(name, email, generate_password_hash(password, method='pbkdf2:sha256'))
        _log_in(new_user)

        # Registered = logged in. No second login form.
        # Straight to Strava's consent screen; the callback then lands on the main panel.
        return redirect(url_for('user.strava_login'))
        # To skip Strava here and open the panel directly instead:
        # return redirect(url_for('token.back_to_panel'))

    return render_template('register.html')


@user_routes.route('/strava_login')
def strava_login():
    """Send the already logged-in user to Strava's consent screen (no credentials form)."""
    if 'user_id' not in session:
        return redirect(url_for('user.login'))

    redirect_uri = url_for('token.exchange_token', _external=True)
    return redirect(get_strava_authorization_url(STRAVA_CLIENT_ID, redirect_uri))


@user_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)

        if user and check_password_hash(user.password_hash, password):
            _log_in(user)
            return redirect(url_for('token.back_to_panel'))

        flash('Invalid email or password. Please try again.')

    return render_template('login.html')


@user_routes.route('/logout')
def logout():
    db_session = SessionLocal()
    try:
        user_id = session.get('user_id')
        
        if user_id:
            strava_token = get_token_logged_user(db_session, user_id)
            if strava_token:
                db_session.delete(strava_token)
                db_session.commit()

        session.clear()
        flash('You have been logged out, and your Strava token has been deleted.')

    except Exception as e:
        db_session.rollback()
        flash(f"An error occurred while logging out: {e}")
    
    finally:
        db_session.close()

    return redirect(url_for('user.login'))


@user_routes.route('/second_window')
def second_window():
    return render_template('templates/second_window.html')

@user_routes.route('/logged_in', methods=['GET'])
def logged_in():
    user_name = session.get('name', 'Guest')
    return render_template('second_window.html', user_name=user_name)