# database/init_db.py
from database.connection import engine, Base, test_connection
from utils.logger import logger

def init_database():
    if test_connection():
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables created successfully")
    else:
        logger.error("Database connection failed. Tables not created.")

if __name__ == "__main__":
    init_database()