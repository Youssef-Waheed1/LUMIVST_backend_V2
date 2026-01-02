
import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert
import math

# 1. Configuration
# Local Database (Source)
LOCAL_DB_URL = "postgresql://postgres:youssef505050@localhost:5432/lumivst_db"

# Remote Database (Destination - Render)
# Read from env or hardcode mostly for this run (using what you provided)
REMOTE_DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"

def migrate_data():
    print("🚀 Starting Data Migration: Local -> Render")
    
    # 2. Connect to Local DB
    print("🔌 Connecting to Local DB...")
    local_engine = create_engine(LOCAL_DB_URL)
    
    try:
        with local_engine.connect() as conn:
            print("📥 Fetching ALL price data from Local DB (this might take a moment)...")
            # Query strictly relevant columns
            query = text("""
                SELECT 
                    date, symbol, close, open, high, low, 
                    volume_traded, value_traded_sar, no_of_trades, 
                    change, change_percent, industry_group, company_name 
                FROM prices
            """)
            df = pd.read_sql(query, conn)
            print(f"✅ Loaded {len(df)} records from Local DB.")
    except Exception as e:
        print(f"❌ Failed to read from Local DB: {e}")
        return

    if df.empty:
        print("⚠️ No data found in Local DB. Exiting.")
        return

    # 3. Connect to Remote DB
    print("🔌 Connecting to Remote DB (Render)...")
    remote_engine = create_engine(REMOTE_DB_URL)

    # 4. Prepare for Bulk Insert (Chunked)
    print("📤 Preparing to upload data to Render...")
    
    # Convert DataFrame to list of dicts for SQLAlchemy
    # Ensure NaN values are handled (Postgres doesn't like NaN for numeric)
    df = df.where(pd.notnull(df), None)
    records = df.to_dict(orient='records')
    
    chunk_size = 5000
    total_records = len(records)
    chunks = math.ceil(total_records / chunk_size)

    print(f"📦 Total chunks to upload: {chunks}")

    from sqlalchemy import Table, MetaData, Column, String, Date, Float, BigInteger, Numeric, Integer

    # Define table structure for core reflection (or just use raw SQL/insert)
    metadata = MetaData()
    prices_table = Table(
        'prices', metadata,
        Column('date', Date, primary_key=True),
        Column('symbol', String, primary_key=True),
        Column('close', Numeric(12, 2)),
        Column('open', Numeric(12, 2)),
        Column('high', Numeric(12, 2)),
        Column('low', Numeric(12, 2)),
        Column('volume_traded', BigInteger),
        Column('value_traded_sar', Numeric(18, 2)),
        Column('no_of_trades', Integer),
        Column('change', Numeric(12, 2)),
        Column('change_percent', Numeric(8, 4)),
        Column('industry_group', String),
        Column('company_name', String)
    )

    success_count = 0

    with remote_engine.connect() as conn:
        # Resuming from Chunk 71 (Index 70)
        start_chunk_index = 70 
        print(f"⏩ Skipping first {start_chunk_index} chunks. Resuming from Chunk {start_chunk_index + 1}...")

        for i in range(start_chunk_index, chunks):
            start = i * chunk_size
            end = start + chunk_size
            batch = records[start:end]
            
            # Construct Upsert Statement
            stmt = insert(prices_table).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=['date', 'symbol'],
                set_={
                    'close': stmt.excluded.close,
                    'open': stmt.excluded.open,
                    'high': stmt.excluded.high,
                    'low': stmt.excluded.low,
                    'volume_traded': stmt.excluded.volume_traded,
                    'value_traded_sar': stmt.excluded.value_traded_sar,
                    'no_of_trades': stmt.excluded.no_of_trades,
                    'change': stmt.excluded.change,
                    'change_percent': stmt.excluded.change_percent,
                    'industry_group': stmt.excluded.industry_group,
                    'company_name': stmt.excluded.company_name
                }
            )
            
            try:
                conn.execute(stmt)
                conn.commit()
                success_count += len(batch)
                print(f"✅ Uploaded Chunk {i+1}/{chunks} ({len(batch)} records)")
            except Exception as e:
                print(f"❌ Error uploading chunk {i+1}: {e}")
                conn.rollback()

    print(f"🎉 Migration Completed! Successfully transferred {success_count} records.")

    # 5. Trigger RS Calculation (Optional but recommended)
    print("\n🧮 Tip: Now you should run 'python scripts/daily_market_update.py' again to calculate RS based on this new data.")

if __name__ == "__main__":
    migrate_data()
