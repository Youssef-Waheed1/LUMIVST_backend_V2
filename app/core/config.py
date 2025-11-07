import os
from dotenv import load_dotenv

load_dotenv()

# إعدادات PostgreSQL - استخدم مباشرة من Environment
DATABASE_URL = os.getenv("DATABASE_URL")

# تأكد من التنسيق الصحيح لـ PostgreSQL
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# إذا مفيش DATABASE_URL (للتطوير المحلي)
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:youssef505050@localhost/lumivst_db"

# إعدادات Redis - استخدم REDIS_URL مباشرة من Railway
REDIS_URL = os.getenv("REDIS_URL")

# إذا مفيش REDIS_URL (للتطوير المحلي)
if not REDIS_URL:
    REDIS_URL = "redis://localhost:7424"

# إعدادات الكاش
CACHE_EXPIRE_SECONDS = int(os.getenv("CACHE_EXPIRE_SECONDS", 86400))  # 24 ساعة
STOCK_PRICE_CACHE_SECONDS = int(os.getenv("STOCK_PRICE_CACHE_SECONDS", 300))  # 5 دقائق

# -------------------------------
STATISTICS_CACHE_EXPIRY: int = 3600  # 1 hour
STATISTICS_CREDITS_COST: int = 50
# --------------------------------

# إعدادات التسجيل
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# باقي الإعدادات الحالية
BASE_URL = "https://api.twelvedata.com"
API_KEY = os.getenv("TWELVE_DATA_API_KEY", "8e06aec81b4d415d905af639ce78449b")

class Settings:
    def __init__(self):
        self.database_url = DATABASE_URL
        self.redis_url = REDIS_URL  # ⭐ أضف هذا
        self.base_url = BASE_URL
        self.api_key = API_KEY

# إنشاء instance
settings = Settings()