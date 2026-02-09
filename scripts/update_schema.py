
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal

def add_columns():
    db = SessionLocal()
    try:
        print("Checking and adding missing columns to stock_indicators table...")
        
        # Check if e45_cfg exists
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='stock_indicators' AND column_name='e45_cfg'"))
        if not result.scalar():
            print("Adding e45_cfg column...")
            db.execute(text("ALTER TABLE stock_indicators ADD COLUMN e45_cfg NUMERIC(5, 2)"))
        else:
            print("e45_cfg already exists.")

        # Check if e20_sma3_rsi3 exists
        result = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='stock_indicators' AND column_name='e20_sma3_rsi3'"))
        if not result.scalar():
            print("Adding e20_sma3_rsi3 column...")
            db.execute(text("ALTER TABLE stock_indicators ADD COLUMN e20_sma3_rsi3 NUMERIC(5, 2)"))
        else:
            print("e20_sma3_rsi3 already exists.")

        db.commit()
        print("Schema update complete.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_columns()
