from sqlalchemy import create_engine, text

DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"

engine = create_engine(DB_URL)

print("🔍 Checking rs_daily_v2 table...")

try:
    with engine.connect() as conn:
        # Check if table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'rs_daily_v2'
            )
        """))
        exists = result.scalar()
        
        if not exists:
            print("❌ Table rs_daily_v2 does NOT exist!")
        else:
            print("✅ Table rs_daily_v2 exists!")
            
            # Get count
            result = conn.execute(text("SELECT COUNT(*) FROM rs_daily_v2"))
            count = result.scalar()
            print(f"📊 Total Records: {count:,}")
            
            if count > 0:
                # Get date range
                result = conn.execute(text("SELECT MIN(date), MAX(date) FROM rs_daily_v2"))
                row = result.fetchone()
                print(f"📅 Date Range: {row[0]} to {row[1]}")
                
                # Get sample
                result = conn.execute(text("""
                    SELECT symbol, date, rs_rating, rs_raw 
                    FROM rs_daily_v2 
                    ORDER BY date DESC, rs_rating DESC 
                    LIMIT 5
                """))
                print("\n🔝 Top 5 Latest Records:")
                for row in result:
                    print(f"   {row[0]} | {row[1]} | RS: {row[2]} | Raw: {row[3]}")
            else:
                print("⚠️  Table is empty!")
                
except Exception as e:
    print(f"❌ Error: {e}")
