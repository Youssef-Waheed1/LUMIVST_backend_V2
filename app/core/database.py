

# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# import os

# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:youssef505050@localhost:5432/lumivst_db")

# # ⭐ زيادة حجم الـ connection pool
# engine = create_engine(
#     DATABASE_URL,
#     pool_size=20,           # ⭐ زيادة من 5 لـ 20
#     max_overflow=30,        # ⭐ زيادة من 10 لـ 30  
#     pool_timeout=30,
#     pool_recycle=1800       # ⭐ إعادة تدوير الاتصالات كل 30 دقيقة
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# # استيراد الـ models بعد تعريف Base
# from app.models.profile import CompanyProfile
# from app.models.quote import StockQuote
# from app.models.technical_indicators import TechnicalIndicator, TechnicalIndicatorData  # ⭐ جديد

# def create_tables():
#     """إنشاء الجداول في قاعدة البيانات"""
#     try:
#         Base.metadata.create_all(bind=engine)
#         print("✅ تم إنشاء الجداول في PostgreSQL بنجاح")
#     except Exception as e:
#         print(f"❌ خطأ في إنشاء الجداول: {e}")

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()  # ⭐ التأكد من إغلاق الاتصال




# app/core/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# ✅ استخدام DATABASE_URL من config
from app.core.config import DATABASE_URL

# ⭐ إعدادات pool محسّنة
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # عدد الاتصالات الأساسي
    max_overflow=30,        # الاتصالات الإضافية ع الحاجة
    pool_timeout=30,        # مهلة الانتظار
    pool_recycle=1800,      # إعادة تدوير الاتصالات كل 30 دقيقة
    echo=False              # ⭐ إيقاف SQL logging (خلي True لو عايز تشوف الـ queries)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# استيراد الـ Models
from app.models.profile import CompanyProfile
from app.models.quote import StockQuote

def create_tables():
    """إنشاء الجداول"""
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