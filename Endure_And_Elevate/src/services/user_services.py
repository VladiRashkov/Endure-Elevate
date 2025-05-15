from src.db.database_models import User, SessionLocal
from sqlalchemy.orm import Session


def get_user_by_email(email: str):
    session = SessionLocal()
    return session.query(User).filter_by(email=email).first()

def create_user(name: str, email: str, hashed_password: str):
    session = SessionLocal()
    new_user = User(name=name, email=email, password_hash=hashed_password)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    session.close()
    return new_user
