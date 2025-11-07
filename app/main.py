

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.redis import redis_cache
from app.core.database import create_tables
import os
from typing import List, Tuple, Optional

class AppConfig:
    """كلاس لتكوين التطبيق"""
    
    def __init__(self):
        self.title = "Saudi Stocks API"
        self.description = "API for Saudi Stock Market data with caching"
        self.version = "1.0.0"
        
        self.cors_origins = [
            "lumivst-frontend-v2-139jc57pc-youssefs-projects-c6c3030a.vercel.app",
            "lumivst-frontend-v2.vercel.app",
            "http://localhost:3000",
        ]
        
        self.routes = [
            {"module": "stocks", "router": "router", "prefix": None},
            {"module": "financials", "router": "router", "prefix": None},
            {"module": "cache", "router": "router", "prefix": None},
            {"module": "profile", "router": "router", "prefix": "/api/v1"},
            {"module": "quote", "router": "router", "prefix": "/api/v1"},
            {"module": "statistics", "router": "router", "prefix": None},
        ]

class Application:
    """كلاس رئيسي لإدارة التطبيق"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.app = FastAPI(
            title=config.title,
            description=config.description,
            version=config.version
        )
        
        self._setup()
    
    def _setup(self):
        """إعداد التطبيق"""
        self._setup_cors()
        self._setup_routes()
        self._setup_handlers()
    
    def _setup_cors(self):
        """إعداد CORS"""
        origins = self.config.cors_origins.copy()
        
        if os.getenv("ENVIRONMENT") == "development":
            origins.extend([
                "http://127.0.0.1:3000",
                "http://localhost:3001",
            ])
        
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """إعداد الـ Routes"""
        for route in self.config.routes:
            try:
                module_path = f"app.api.routes.{route['module']}"
                module = __import__(module_path, fromlist=[route['router']])
                router = getattr(module, route['router'])
                
                if route['prefix']:
                    self.app.include_router(router, prefix=route['prefix'])
                else:
                    self.app.include_router(router)
                    
                print(f"✅ تم تحميل {route['module']} router")
                
            except ImportError as e:
                print(f"⚠️ خطأ في تحميل {route['module']}: {e}")
    
    def _setup_handlers(self):
        """إعداد الـ event handlers والـ endpoints"""
        
        @self.app.on_event("startup")
        async def startup_event():
            print("🚀 Starting Saudi Stocks API...")
            create_tables()
            
            redis_connected = await redis_cache.init_redis()
            if not redis_connected:
                print("⚠️  سيتم العمل بدون كاش Redis")
            else:
                print("✅ Redis cache initialized successfully")
        
        @self.app.get("/")
        async def root():
            return {
                "message": self.config.title,
                "version": self.config.version,
                "docs": "/docs"
            }
        
        @self.app.get("/health")
        async def health_check():
            redis_status = "connected" if redis_cache.redis_client else "disconnected"
            return {
                "status": "healthy",
                "redis": redis_status,
                "app": self.config.title,
                "message": "API is running" + (" with cache" if redis_cache.redis_client else " without cache")
            }

# إنشاء التطبيق
config = AppConfig()
app = Application(config).app




























# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from app.core.redis import redis_cache
# from app.core.database import create_tables  # ⭐ أضف هذا
# from app.api.routes import stocks, financials, cache, profile, quote
# import os

# app = FastAPI(
#     title="Saudi Stocks API",
#     description="API for Saudi Stock Market data with caching",
#     version="1.0.0"
# )

# # ⚡ إعداد CORS ديناميكي بناءً على البيئة
# origins = [
#     "https://lumivst-frontend-git-main-youssefs-projects-c6c3030a.vercel.app",
#     "https://lumivst-frontend.vercel.app",
#     "http://localhost:3000",
# ]

# if os.getenv("ENVIRONMENT") == "development":
#     origins.extend([
#         "http://127.0.0.1:3000",
#         "http://localhost:3001",
#     ])

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#     allow_headers=["*"],
# )

# # ⭐ إضافة كل الـ routes


# # app.include_router(financials.router, prefix="/api")  # ⭐ إضافة prefix
# # app.include_router(cache.router, prefix="/api")  # ⭐ إضافة prefix
# app.include_router(stocks.router)
# app.include_router(financials.router)
# app.include_router(cache.router)
# app.include_router(profile.router, prefix="/api/v1")
# app.include_router(quote.router, prefix="/api/v1")

# @app.on_event("startup")
# async def startup_event():
#     """تهيئة الاتصالات عند بدء التشغيل"""
#     print("🚀 Starting Saudi Stocks API...")
    
#     # ⭐ إنشاء الجداول في PostgreSQL
#     create_tables()
    
#     # تهيئة Redis
#     redis_connected = await redis_cache.init_redis()
#     if not redis_connected:
#         print("⚠️  سيتم العمل بدون كاش Redis")
#     else:
#         print("✅ Redis cache initialized successfully")

# @app.get("/")
# async def root():
#     return {
#         "message": "Saudi Stocks API with Redis Caching",
#         "version": "1.0.0",
#         "docs": "/docs"
#     }

# @app.get("/health")
# async def health_check():
#     """فحص صحة التطبيق والكاش"""
#     redis_status = "connected" if redis_cache.redis_client else "disconnected"
#     return {
#         "status": "healthy",
#         "redis": redis_status,
#         "timestamp": "2024-01-01T00:00:00Z",
#         "message": "API is running" + (" with cache" if redis_cache.redis_client else " without cache")
#     }