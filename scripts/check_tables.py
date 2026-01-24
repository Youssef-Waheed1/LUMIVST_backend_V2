from sqlalchemy import create_engine, inspect
import os
from app.core.config import settings

# Override database URL if needed or rely on env
DATABASE_URL = settings.DATABASE_URL

def list_tables():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("📋 Existing Tables:")
    for t in tables:
        print(f" - {t}")

if __name__ == "__main__":
    list_tables()
