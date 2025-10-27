from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL
import redis
from datetime import datetime, timedelta

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

# إعداد Redis للـ Cache
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# دالة للتحقق من اتصال Redis
def is_redis_available():
    try:
        redis_client.ping()
        return True
    except redis.ConnectionError:
        return False