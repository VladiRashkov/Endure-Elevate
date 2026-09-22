# src/services/token_services.py
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy.orm import Session

from src.db.database_models import StravaToken

STRAVA_TOKEN_URL = 'https://www.strava.com/oauth/token'
REFRESH_MARGIN = timedelta(minutes=2)  # refresh a little early, not at the last second


def _utcnow_naive() -> datetime:
    """Naive UTC 'now', matching how expires_at is stored (utcnow() is deprecated)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _epoch_to_utc_naive(epoch_seconds: int) -> datetime:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).replace(tzinfo=None)


def get_token_logged_user(session: Session, user_id: int):
    return session.query(StravaToken).filter(StravaToken.user_id == user_id).first()


def save_strava_tokens(session: Session, user_id: int, access_token: str, refresh_token: str, expires_at: int):
    token = get_token_logged_user(session, user_id)
    if token is None:
        token = StravaToken(user_id=user_id)
        session.add(token)

    token.access_token = access_token
    token.refresh_token = refresh_token
    token.expires_at = _epoch_to_utc_naive(expires_at)
    session.commit()  # runs for new AND existing tokens


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    response = requests.post(STRAVA_TOKEN_URL, data=payload, timeout=10)
    if response.status_code != 200:
        raise RuntimeError(f'Failed to refresh token: {response.status_code}, {response.text}')
    return response.json()


def get_valid_access_token(session: Session, user_id: int, client_id: str, client_secret: str):
    """Return a usable access token for this user, refreshing it if it is about to expire.

    Returns None if the user never connected Strava. Raises if a refresh fails.
    Strava rotates the refresh token on every refresh, so the new pair is saved.
    """
    token = get_token_logged_user(session, user_id)
    if token is None or not token.access_token:
        return None

    if token.expires_at and token.expires_at > _utcnow_naive() + REFRESH_MARGIN:
        return token.access_token

    fresh = refresh_access_token(client_id, client_secret, token.refresh_token)
    save_strava_tokens(session, user_id, fresh['access_token'], fresh['refresh_token'], fresh['expires_at'])
    return fresh['access_token']
