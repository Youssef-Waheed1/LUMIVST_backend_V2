from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from app.core.config import DATABASE_URL  # ⭐ استيراد من config

# استخدام DATABASE_URL من الإعدادات
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_timeout=30,
    pool_recycle=1800
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# استيراد الـ models بعد تعريف Base
from app.models.profile import CompanyProfile
from app.models.quote import StockQuote

def create_tables():
    """إنشاء الجداول في قاعدة البيانات"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ تم إنشاء الجداول في PostgreSQL بنجاح")
    except Exception as e:
        print(f"❌ خطأ في إنشاء الجداول: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()