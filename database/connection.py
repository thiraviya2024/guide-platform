# database/connection.py
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Database URL - try from config first, then fallback to env
try:
    from config.settings import LOG_LEVEL
except ImportError:
    LOG_LEVEL = "INFO"

DATABASE_URL = os.getenv("DATABASE_URL")
MIMIC_DATABASE_URL = os.getenv("MIMIC_DATABASE_URL")

# If MIMIC_DATABASE_URL is not set, use the same as DATABASE_URL
if not MIMIC_DATABASE_URL:
    MIMIC_DATABASE_URL = DATABASE_URL
    print("⚠️ MIMIC_DATABASE_URL not set, using DATABASE_URL")

if not DATABASE_URL:
    # Fallback for local development
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/lipidai"
    print("⚠️ DATABASE_URL not set, using default local connection")

# Create main engine
engine = create_engine(
    DATABASE_URL, 
    pool_pre_ping=True, 
    echo=False,
    pool_size=5,
    max_overflow=10
)

# Create MIMIC engine (if different)
if MIMIC_DATABASE_URL != DATABASE_URL:
    mimic_engine = create_engine(
        MIMIC_DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
        pool_size=5,
        max_overflow=10
    )
else:
    mimic_engine = engine

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
MIMICSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mimic_engine)

Base = declarative_base()

def get_db():
    """Get database session for lipid data."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_mimic_db():
    """Get database session for MIMIC data."""
    db = MIMICSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    """Test connection to lipid database."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("✅ Lipid database connected successfully")
            return True
    except Exception as e:
        print(f"❌ Lipid database connection failed: {e}")
        return False

def test_mimic_connection():
    """Test connection to MIMIC database."""
    try:
        with mimic_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("✅ MIMIC database connected successfully")
            return True
    except Exception as e:
        print(f"❌ MIMIC database connection failed: {e}")
        return False

def test_all_connections():
    """Test all database connections."""
    lipid_ok = test_connection()
    mimic_ok = test_mimic_connection()
    
    if lipid_ok and mimic_ok:
        print("✅ All databases connected successfully!")
    else:
        print("⚠️ Some database connections failed.")

if __name__ == "__main__":
    test_all_connections()