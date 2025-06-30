import logging

from rgs_interface.config import load_config
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)


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
        connection_string = (
            f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
        )
        engine = create_engine(connection_string, pool_pre_ping=True)

        logger.info("Database engine created successfully - %s", db_name)
        return engine

    except Exception as e:
        logger.critical("Database engine creation failed: %s", e)
        return None
