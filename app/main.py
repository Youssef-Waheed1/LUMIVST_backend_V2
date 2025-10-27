from fastapi import FastAPI
from app.core.redis import redis_cache
from app.api.routes import companies, financials, cache

app = FastAPI(title="Saudi Stocks API")

# إضافة الـ routes
app.include_router(companies.router)
app.include_router(financials.router)
app.include_router(cache.router)

@app.on_event("startup")
async def startup_event():
    """تهيئة الاتصالات عند بدء التشغيل"""
    redis_connected = await redis_cache.init_redis()
    if not redis_connected:
        print("⚠️  سيتم العمل بدون كاش Redis")

@app.get("/")
async def root():
    return {"message": "Saudi Stocks API with Redis Caching"}

@app.get("/health")
async def health_check():
    """فحص صحة التطبيق والكاش"""
    redis_status = "connected" if redis_cache.redis_client else "disconnected"
    return {
        "status": "healthy",
        "redis": redis_status,
        "message": "API is running" + (" with cache" if redis_cache.redis_client else " without cache")
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lumivst-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)