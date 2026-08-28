"""Read-only database connectivity check; configuration comes from the environment."""
from app.core.database import check_db_connection

if __name__ == "__main__":
    print("Database connection available" if check_db_connection() else "Database connection unavailable")
