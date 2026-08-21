import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env")
    exit()

try:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("\n✅ CONNECTED TO NEON POSTGRESQL\n")

        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))

        tables = [row[0] for row in result]

        print("========== TABLES ==========")

        for table in tables:
            print(f"📁 {table}")

        print("\n========== ROW COUNTS ==========")

        for table in tables:
            try:
                count = conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                ).scalar()

                print(f"{table}: {count} rows")

            except Exception as e:
                print(f"{table}: ERROR - {e}")

except Exception as e:
    print("\n❌ DATABASE CONNECTION FAILED")
    print(e)
    