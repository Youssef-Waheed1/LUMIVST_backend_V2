# reset_alembic.py

from app.core.database import engine
from sqlalchemy import text

# مسح الجدول تماماً
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    conn.commit()
    print("✅ تم حذف جدول alembic_version")