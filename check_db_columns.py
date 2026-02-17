from sqlalchemy import create_engine, inspect

db_url = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"
engine = create_engine(db_url)
inspector = inspect(engine)
cols = sorted([c['name'] for c in inspector.get_columns('stock_indicators')])

# Check for the specific columns  
target_cols = ['rsi_14_9days_ago_w', 'stamp_a_value_w', 'stamp_s9rsi_w', 'stamp_e45cfg_w', 'stamp_e45rsi_w', 'stamp_e20sma3_w']
for col in target_cols:
    if col in cols:
        print(f"✓ {col}")
    else:
        print(f"✗ {col} - MISSING")

print(f"\nTotal columns: {len(cols)}")
print("\nAll columns:")
for col in cols:
    print(f"  - {col}")
