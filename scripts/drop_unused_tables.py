
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def drop_tables():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in .env")
        return

    tables_to_drop = ["balance_sheets", "cash_flows", "income_statements"]
    
    print(f"Connecting to database...")
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as connection:
            # Start a transaction
            trans = connection.begin()
            try:
                for table_name in tables_to_drop:
                    print(f"Dropping table: {table_name}...")
                    connection.execute(text(f"DROP TABLE IF EXISTS \"{table_name}\" CASCADE"))
                    print(f"✅ Table {table_name} dropped successfully.")
                
                trans.commit()
                print("\nAll specified tables have been dropped.")
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during dropping tables: {e}")
                
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    confirm = input("Are you sure you want to drop balance_sheets, cash_flows, and income_statements? (y/n): ")
    if confirm.lower() == 'y':
        drop_tables()
    else:
        print("Operation cancelled.")
