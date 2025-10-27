import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
from datetime import datetime, timedelta

# قراءة رابط قاعدة البيانات من متغير البيئة (Railway)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:youssef505050@localhost:5432/lumivst_db")

# إنشاء engine لقاعدة البيانات
engine = create_engine(DATABASE_URL)

# إنشاء SessionLocal للتعامل مع قاعدة البيانات
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# إنشاء Base للنماذج
Base = declarative_base()

# Dependency للحصول على جلسة قاعدة البيانات
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ إعداد Redis من متغير البيئة REDIS_URL
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("✅ تم الاتصال بـ Redis بنجاح")
except redis.ConnectionError:
    redis_client = None
    print("❌ فشل الاتصال بـ Redis. سيتم العمل بدون كاش")

# دالة للتحقق من اتصال Redis
def is_redis_available():
    if not redis_client:
        return False
    try:
        redis_client.ping()
        return True
    except redis.ConnectionError:
        return False
