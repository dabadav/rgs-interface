import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables from `.env`
load_dotenv()

def get_db_engine():
    """Create and return a SQLAlchemy engine for MySQL."""
    try:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_name = os.getenv("DB_NAME")

        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Missing database credentials in environment variables")

        # Create the database connection string
        connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
        engine = create_engine(connection_string, pool_pre_ping=True)

        print("Database engine created successfully")
        return engine

    except Exception as e:
        print(f"Database engine creation failed: {e}")
        return None
