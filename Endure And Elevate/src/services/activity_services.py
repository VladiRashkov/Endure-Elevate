import pandas as pd
from src.api_methods.authorize import access_activity_data
from src.data_preprocessing.preprocess import preprocess_data
from sqlalchemy.orm import sessionmaker, Session
from src.db.database_models import engine, Activity, User

SessionLocal = sessionmaker(bind=engine)

def fetch_and_preprocess_activities(access_token, user_id):
    dfs_to_concat = []
    page_number = 1

    while True:
        
        data = access_activity_data(access_token, params={'per_page': 200, 'page': page_number})
        if not data:
            break
       
        dfs_to_concat.append(preprocess_data(data))
        page_number += 1

    if dfs_to_concat:
        df = pd.concat(dfs_to_concat, ignore_index=True)
        df = df[df['type'].str.strip() == 'Run']  

        
        session_db = SessionLocal()
        user = session_db.query(User).filter(User.id == user_id).first()

        try:
            for _, row in df.iterrows():
                activity = Activity(
                    id=row["id"],
                    name=row["name"],
                    type=row["type"],
                    distance=row["distance"],
                    moving_time=row["moving_time"],
                    total_elevation_gain=row["total_elevation_gain"],
                    start_date=row["start_date"],
                    average_heartrate=row.get("average_heartrate"),
                    max_heartrate=row.get("max_heartrate"),  
                    polyline_data=row.get("map").get("summary_polyline"),  
                    average_cadence=row.get("average_cadence"), 
                    elevation_high=row.get("elev_high"),  
                    elevation_low=row.get("elev_low"),  
                    calories=row.get("calories") 
                )

                user.activities.append(activity)
                session_db.merge(activity)  

            session_db.commit()
        except Exception as e:
            session_db.rollback()
            print(f"Error saving activities to the database: {e}")
        finally:
            session_db.close()

        return df 

    else:
        print("No activities to process.")
        return pd.DataFrame()


def get_recent_activity(session: Session, user_id: int):
    return (
        session.query(Activity)
        .filter(Activity.user_id == user_id) 
        .order_by(Activity.start_date.desc())
        .first() 
    )