"""
Load MIMIC-IV Demo Data into PostgreSQL
This loads the ACTUAL MIMIC-IV dataset from your downloaded files
"""

import os
import pandas as pd
import gzip
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Your MIMIC-IV demo data path
MIMIC_PATH = r"C:\Users\THIYA\Downloads\mimic-iv-clinical-database-demo-2.2\mimic-iv-clinical-database-demo-2.2"

# MIMIC database connection (separate database)
MIMIC_DATABASE_URL = "postgresql://postgres:Thiya%402020@localhost:5432/mimic_demo"

def create_mimic_database():
    """Create MIMIC database if it doesn't exist."""
    default_url = "postgresql://postgres:Thiya%402020@localhost:5432/postgres"
    engine = create_engine(default_url)
    
    try:
        with engine.connect() as conn:
            conn.execute(text("COMMIT"))
            result = conn.execute(text(
                "SELECT 1 FROM pg_database WHERE datname = 'mimic_demo'"
            ))
            if not result.fetchone():
                conn.execute(text("CREATE DATABASE mimic_demo"))
                print("✅ MIMIC database created!")
            else:
                print("ℹ️ MIMIC database already exists")
    except Exception as e:
        print(f"❌ Error creating database: {e}")

def load_mimic_files():
    """Load all MIMIC-IV CSV files into PostgreSQL."""
    engine = create_engine(MIMIC_DATABASE_URL)
    
    # Load hosp files
    hosp_path = os.path.join(MIMIC_PATH, 'hosp')
    if os.path.exists(hosp_path):
        print("\n📂 Loading HOSP files...")
        for file in os.listdir(hosp_path):
            if file.endswith('.csv.gz'):
                table_name = file.replace('.csv.gz', '')
                print(f"   Loading {table_name}...")
                try:
                    df = pd.read_csv(os.path.join(hosp_path, file))
                    df.to_sql(table_name, engine, if_exists='replace', index=False)
                    print(f"   ✅ Loaded {len(df)} rows to {table_name}")
                except Exception as e:
                    print(f"   ❌ Error loading {table_name}: {e}")
    
    # Load icu files
    icu_path = os.path.join(MIMIC_PATH, 'icu')
    if os.path.exists(icu_path):
        print("\n📂 Loading ICU files...")
        for file in os.listdir(icu_path):
            if file.endswith('.csv.gz'):
                table_name = file.replace('.csv.gz', '')
                print(f"   Loading {table_name}...")
                try:
                    df = pd.read_csv(os.path.join(icu_path, file))
                    df.to_sql(table_name, engine, if_exists='replace', index=False)
                    print(f"   ✅ Loaded {len(df)} rows to {table_name}")
                except Exception as e:
                    print(f"   ❌ Error loading {table_name}: {e}")

def main():
    print("=" * 60)
    print("MIMIC-IV DEMO DATA LOADER")
    print("=" * 60)
    
    print("\n📁 Creating MIMIC database...")
    create_mimic_database()
    
    print("\n📁 Loading MIMIC data files...")
    print("   This may take a few minutes...")
    load_mimic_files()
    
    print("\n" + "=" * 60)
    print("✅ MIMIC-IV Demo Data Load Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()