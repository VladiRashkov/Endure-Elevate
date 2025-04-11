from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, BigInteger, Text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=func.now())

    activities = relationship("Activity", back_populates="user")  
   
    strava_token = relationship("StravaToken", back_populates="user", uselist=False)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  
    name = Column(String(200))  
    type = Column(String(50))  
    distance = Column(Float)  
    moving_time = Column(Integer)  
    total_elevation_gain = Column(Float)  
    start_date = Column(String) 
    average_heartrate = Column(Float)  
    max_heartrate = Column(Float)  
    polyline_data = Column(Text)  
    average_cadence = Column(Float)  
    elevation_high = Column(Float)  
    elevation_low = Column(Float) 
    calories = Column(Float)

    
    user = relationship("User", back_populates="activities")


class StravaToken(Base):
    __tablename__ = 'strava_tokens'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)  # Foreign key linking to User
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)

   
    user = relationship("User", back_populates="strava_token")

Base.metadata.create_all(bind=engine)
# from sqlalchemy import create_engine, Column, Integer, String, Float,\
# ForeignKey, DateTime, BigInteger, Table, Text
# from sqlalchemy.orm import sessionmaker, relationship, declarative_base
# from sqlalchemy.sql import func
# import datetime

# # Database URL for SQLite
# DATABASE_URL = "sqlite:///./test.db"
# engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# # Define the User model

# user_activities = Table(
#     'user_activities',  # Name of the linking table
#     Base.metadata,
#     Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
#     Column('activity_id', Integer, ForeignKey('activities.id'), primary_key=True)
# )
# class User(Base):
#     __tablename__ = "users"  

#     id = Column(Integer, primary_key=True)
#     name = Column(String(100), nullable=False)
#     email = Column(String(150), unique=True, nullable=False)
#     password_hash = Column(String(200), nullable=False)
#     created_at = Column(DateTime, default=func.now())  # Use func.now() for a database-side timestamp

#     activities = relationship("Activity", secondary=user_activities, back_populates="user") 
    
#     strava_token = relationship("StravaToken", back_populates="user", uselist=False)
#     # Relationship to Activity table

# # Define the Activity model
# class Activity(Base):
#     __tablename__ = "activities"  # Specify the table name

#     id = Column(BigInteger, primary_key=True)
#     name = Column(String(200))  # Name of the activity (e.g., "Morning Run")
#     type = Column(String(50))  # Type of activity (e.g., "Run", "Ride")
#     distance = Column(Float)  # Distance covered in meters
#     moving_time = Column(Integer)  # Time spent moving, in seconds
#     total_elevation_gain = Column(Float)  # Total elevation gain in meters
#     start_date = Column(String)  # Start date and time in UTC
#     average_heartrate = Column(Float)  # Average heartrate during the activity
#     max_heartrate = Column(Float)  # Maximum heartrate recorded during the activity
#     polyline_data = Column(Text)  # Encoded polyline string for mapping the route
#     average_cadence = Column(Float)  # Average cadence (revolutions per minute)
#     elevation_high = Column(Float)  # Highest elevation point in meters
#     elevation_low = Column(Float)  # Lowest elevation point in meters
#     calories = Column(Float)  # Calories burned during the activity

#     user = relationship("User", secondary="user_activities", back_populates="activities")
    
    
# class StravaToken(Base):
#     __tablename__ = 'strava_tokens'
#     id = Column(Integer, primary_key=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
#     access_token = Column(String, nullable=False)
#     refresh_token = Column(String, nullable=False)
#     expires_at = Column(DateTime, nullable=False)
#     user = relationship("User", back_populates="strava_token")

# Base.metadata.create_all(bind=engine)
