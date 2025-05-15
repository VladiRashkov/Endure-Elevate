from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from src.services.user_services import get_user_by_email, create_user
from src.api_methods.authorize import get_strava_authorization_url
from src.utils.helpers import password_validation
from src.db.database_models import SessionLocal, StravaToken
from src.services.token_services import get_token_logged_user

user_routes = Blueprint('user', __name__)

@user_routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        test_password = password_validation(password)

        if not test_password:
            flash('The password must contain at least 8 characters, 1 digit, 1 capital letter, 1 small letter, and 1 special character.')
            return redirect(url_for('user.register'))

        user = get_user_by_email(email)
        if user:
            flash('Email already exists. Please log in.')
            return redirect(url_for('user.login'))

        new_user = create_user(name, email, generate_password_hash(password, method='pbkdf2:sha256'))
        session['user_id'] = new_user.id
        session['email'] = new_user.email

        
        return redirect(url_for('user.strava_login'))

    return render_template('register.html')

@user_routes.route('/strava_login', methods=['GET', 'POST'])
def strava_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['email'] = user.email

            
            client_id = "153633"
            redirect_uri = url_for('token.exchange_token', _external=True)
            auth_url = get_strava_authorization_url(client_id, redirect_uri)

            return redirect(auth_url)

        flash('Invalid email or password. Please try again.')

    return render_template('strava_login.html')

@user_routes.route('/login', methods=['GET', 'POST'])
def login():
    session.pop('_flashes', None)
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = get_user_by_email(email)

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['email'] = user.email
            
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