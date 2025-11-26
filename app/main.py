from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import stocks, financials, cache, statistics, technical_indicators, auth, contact
from app.core.redis import redis_cache
from app.core.database import create_tables
from app.services.cache.stock_cache import SAUDI_STOCKS
from app.services.rs_rating import calculate_all_rs_ratings
import asyncio
from app.core.config import settings 

app = FastAPI(
    title="Saudi Stocks API",
    description="API for Saudi Stock Market data",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def _calculate_and_save_rs(symbols: list):
    """دالة خلفية لحساب RS وحفظه في DB"""
    try:
        rs_data = await calculate_all_rs_ratings(symbols)
        
        if not rs_data:
            print("❌ No RS data calculated")
            return
        
        from app.core.database import get_db
        from app.models.quote import StockQuote
        
        db = next(get_db())
        
        try:
            for symbol, rs_scores in rs_data.items():
                quote = db.query(StockQuote).filter(StockQuote.symbol == symbol).first()
                if quote:
                    for key, value in rs_scores.items():
                        if hasattr(quote, key):
                            setattr(quote, key, value)
            
            db.commit()
            print(f"✅ RS ratings saved to DB for {len(rs_data)} stocks")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Error saving RS to DB: {e}")
        finally:
            db.close()
            
        await redis_cache.delete("tadawul:all:Saudi Arabia")
        
    except Exception as e:
        print(f"❌ Error in background RS calculation: {e}")

# Register routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(stocks.router)
app.include_router(financials.router)
app.include_router(cache.router)
app.include_router(statistics.router)
app.include_router(technical_indicators.router)
app.include_router(contact.router, prefix="/api")

# Event handlers
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Saudi Stocks API...")
    create_tables()
    
    redis_connected = await redis_cache.init_redis()
    if not redis_connected:
        print("⚠️ سنتحدث بدون كاش Redis")
    else:
        print("✅ Redis cache initialized successfully")
    
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    
    @scheduler.scheduled_job('cron', hour=22, minute=0)
    async def daily_rs_update():
        print("🔄 Running daily RS update...")
        await _calculate_and_save_rs(list(SAUDI_STOCKS))
    
    scheduler.start()
    print("✅ Scheduler started for daily RS updates")

@app.get("/")
async def root():
    return {
        "message": "Saudi Stocks API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """فحص صحة التطبيق"""
    import datetime
    
    redis_status = "connected" if redis_cache.redis_client else "disconnected"
    return {
        "status": "healthy",
        "redis": redis_status,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "message": "API is running" + (" with cache" if redis_cache.redis_client else " without cache")
    }