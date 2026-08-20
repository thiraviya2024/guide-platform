# check_db.py
"""
Check Neon PostgreSQL Database
"""

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://neondb_owner:npg_Br9oSefKvHn2@ep-restless-pine-azbzbjcn-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

print("🔍 Connecting to Neon PostgreSQL...")
print("=" * 50)

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        # Test connection
        result = conn.execute(text("SELECT 1")).fetchone()
        print("✅ Connection successful!")
        
        # List all tables
        tables = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)).fetchall()
        
        print(f"\n📊 Tables in database: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check rule counts for each module
        print("\n📈 Clinical Rule Counts:")
        rule_tables = ['lipid_rules', 'cbc_rules', 'lft_rules', 'kft_rules', 
                       'thyroid_rules', 'diabetes_rules', 'vitamins_rules', 'electrolytes_rules']
        total_rules = 0
        
        for table in rule_tables:
            try:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
                print(f"  {table}: {count} rules")
                total_rules += count
            except Exception as e:
                print(f"  {table}: ❌ Not found - {e}")
        
        print(f"\n📊 TOTAL RULES: {total_rules}")
        
        # Check dataset versions
        versions = conn.execute(text("SELECT * FROM dataset_versions ORDER BY created_at DESC")).fetchall()
        if versions:
            print("\n📁 Dataset Versions:")
            for v in versions:
                print(f"  - v{v[1]} ({v[2]}) - {'✅ Active' if v[5] else '📄 Draft'}")
        else:
            print("\n📁 No dataset versions found")
        
        print("\n✅ Database check complete!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    print("\n💡 Make sure:")
    print("  1. Your internet connection is working")
    print("  2. The DATABASE_URL in .env is correct")
    print("  3. Neon database is running")