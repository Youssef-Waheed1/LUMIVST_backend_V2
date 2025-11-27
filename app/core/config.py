# app/core/config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # ⚠️ إزالة القيم الافتراضية المحلية في الإنتاج
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        self.REDIS_URL = os.getenv("REDIS_URL")
        self.CACHE_EXPIRE_SECONDS = int(os.getenv("CACHE_EXPIRE_SECONDS", "300"))
        self.STOCK_PRICE_CACHE_SECONDS = int(os.getenv("STOCK_PRICE_CACHE_SECONDS", "300"))
        self.API_KEY = os.getenv("TWELVE_DATA_API_KEY")
        self.BASE_URL = "https://api.twelvedata.com"
        
        # ⚠️ تحديث الـ CORS للإنتاج
        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,https://www.rebh.ai")
        self.ALLOWED_ORIGINS = [origin.strip() for origin in allowed_origins_str.split(",")]
        
        # إعدادات إضافية مهمة للإنتاج
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

        # Email Settings
        self.SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@lumivst.com")

settings = Settings()




# # app/core/config.py
# import os
# from dotenv import load_dotenv

# load_dotenv()

# # إعدادات PostgreSQL
# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:youssef505050@localhost/lumivst_db")

# # إعدادات Redis
# REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
# REDIS_PORT = int(os.getenv("REDIS_PORT", 7424))
# REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
# REDIS_URL = os.getenv("REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}")

# # إعدادات الكاش
# CACHE_EXPIRE_SECONDS = int(os.getenv("CACHE_EXPIRE_SECONDS", 86400))  # 24 ساعة
# STOCK_PRICE_CACHE_SECONDS = int(os.getenv("STOCK_PRICE_CACHE_SECONDS", 300))  # 5 دقائق

# # -------------------------------
# STATISTICS_CACHE_EXPIRY: int = 3600  # 1 hour
# STATISTICS_CREDITS_COST: int = 50
# # --------------------------------

# # إعدادات التسجيل
# LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# # إعدادات Twelve Data
# BASE_URL = "https://api.twelvedata.com"
# API_KEY = os.getenv("TWELVE_DATA_API_KEY", "8e06aec81b4d415d905af639ce78449b")

# class Settings:
#     def __init__(self):
#         self.database_url = DATABASE_URL
#         self.redis_url = REDIS_URL
#         self.redis_host = REDIS_HOST
#         self.redis_port = REDIS_PORT
#         self.redis_password = REDIS_PASSWORD
#         self.cache_expire_seconds = CACHE_EXPIRE_SECONDS
#         self.stock_price_cache_seconds = STOCK_PRICE_CACHE_SECONDS
#         self.base_url = BASE_URL
#         self.api_key = API_KEY
#         self.log_level = LOG_LEVEL

# # إنشاء instance
# settings = Settings()










