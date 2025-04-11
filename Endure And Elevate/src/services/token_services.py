from src.db.database_models import StravaToken
from sqlalchemy.orm import Session
from datetime import datetime
import requests
def save_strava_tokens(session: Session, user_id: int, access_token: str, refresh_token: str, expires_at: int):
    expires_at_datetime = datetime.utcfromtimestamp(expires_at)
    existing_token = session.query(StravaToken).filter_by(user_id=user_id).first()
    if existing_token:
    
        existing_token.access_token = access_token
        existing_token.refresh_token = refresh_token
        existing_token.expires_at = expires_at_datetime
        
    else:
        
        new_token = StravaToken(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at_datetime,
            
        )
        session.add(new_token)
    session.commit()

def get_token_logged_user(session:Session, user_id:int):
    return session.query(StravaToken).filter(StravaToken.user_id==user_id).first()

def refresh_access_token(client_id:int, clint_secret: int, refresh_token:int):
    token_url = 'https:/www.strava.com/oauth/token'
    payload = {
        'client_id': client_id,
        'client_secred': clint_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token        
    }
    response = requests.post(token_url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to refresh token: {response.status_code}, {response.text}")
        