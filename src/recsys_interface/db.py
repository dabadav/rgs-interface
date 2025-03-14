from sqlalchemy import create_engine
from recsys_interface.config import load_config

def get_db_engine():
    """Create and return a SQLAlchemy engine for MySQL."""
    try:
        credentials = load_config()

        db_user = credentials["DB_USER"]
        db_password = credentials["DB_PASS"]
        db_host = credentials["DB_HOST"]
        db_name = credentials["DB_NAME"]

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
