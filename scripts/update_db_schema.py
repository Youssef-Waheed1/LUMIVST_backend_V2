"""
Auto-sync database schema with SQLAlchemy model.
Reads ALL columns from StockIndicator model and ensures they exist in the DB.
"""
import sys
import os

# Add the parent directory (backend) to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine
from app.models.stock_indicators import StockIndicator
from sqlalchemy import text, inspect

def get_sqlalchemy_column_type(col):
    """Convert SQLAlchemy column type to PostgreSQL type string."""
    col_type = str(col.type)
    
    # Handle Boolean
    if 'BOOLEAN' in col_type.upper():
        default = 'DEFAULT FALSE' if col.default and col.default.arg == False else ''
        return f"BOOLEAN {default}".strip()
    
    # Handle Integer
    if 'INTEGER' in col_type.upper():
        return "INTEGER DEFAULT 0" if col.default else "INTEGER"
    
    # Handle Numeric
    if 'NUMERIC' in col_type.upper():
        return col_type  # Already formatted like NUMERIC(5, 2)
    
    # Handle DateTime
    if 'DATETIME' in col_type.upper() or 'TIMESTAMP' in col_type.upper():
        return "TIMESTAMP"
    
    # Handle String/VARCHAR
    if 'VARCHAR' in col_type.upper() or 'STRING' in col_type.upper():
        return col_type
    
    return col_type

def sync_schema():
    print("🔍 Auto-syncing database schema with StockIndicator model...")
    print("=" * 60)
    
    # Get all columns from the SQLAlchemy model
    model_columns = {}
    for col in StockIndicator.__table__.columns:
        model_columns[col.name] = col
    
    # Get existing columns from the database
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'stock_indicators'
        """))
        db_columns = {row[0] for row in result}
    
    print(f"📋 Model has {len(model_columns)} columns")
    print(f"📋 Database has {len(db_columns)} columns")
    
    # Find missing columns
    missing = []
    for col_name, col in model_columns.items():
        if col_name not in db_columns:
            missing.append((col_name, col))
    
    if not missing:
        print("\n✅ All columns are in sync! Nothing to do.")
        return
    
    print(f"\n⚠️  Found {len(missing)} missing columns:")
    for col_name, _ in missing:
        print(f"   - {col_name}")
    
    # Add missing columns
    print("\n🔧 Adding missing columns...")
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for col_name, col in missing:
            pg_type = get_sqlalchemy_column_type(col)
            try:
                sql = f"ALTER TABLE stock_indicators ADD COLUMN IF NOT EXISTS {col_name} {pg_type}"
                conn.execute(text(sql))
                print(f"   ✅ Added: {col_name} ({pg_type})")
            except Exception as e:
                print(f"   ❌ Failed: {col_name} - {e}")
    
    print("\n" + "=" * 60)
    print("✅ Schema sync complete!")

if __name__ == "__main__":
    sync_schema()
