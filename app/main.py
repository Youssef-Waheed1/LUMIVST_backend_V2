from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import stocks, financials, cache, statistics, technical_indicators, auth, contact, rs, admin
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

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
# Register routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(contact.router, prefix="/api")

# Protected Routers (Require Authentication)
from fastapi import Depends
from app.core.auth import verify_token

protected_dependencies = [Depends(verify_token)]

app.include_router(stocks.router, dependencies=protected_dependencies)
app.include_router(financials.router, dependencies=protected_dependencies)
app.include_router(cache.router, dependencies=protected_dependencies)
app.include_router(statistics.router, dependencies=protected_dependencies)
app.include_router(technical_indicators.router, dependencies=protected_dependencies)
app.include_router(rs.router, prefix="/api", dependencies=protected_dependencies)
app.include_router(admin.router, dependencies=protected_dependencies) # Ensure admin is also double-checked or relies on internal checks

# Event handlers
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting Saudi Stocks API...")
    
    # 1. Run Alembic Migrations Programmatically
    try:
        from alembic.config import Config
        from alembic import command
        
        # Point to alembic.ini (Make sure path is correct relative to CWD)
        # Using uvicorn from root d:\Work\LUMIVST\backend usually
        alembic_cfg = Config("alembic.ini")
        # Ensure the DATABASE_URL is set in the config from environment
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        print("🔄 Running Alembic migrations...")
        # Run synchronous command in executor to avoid blocking async loop? 
        # Actually startup is async but `command.upgrade` is blocking sync code.
        # Ideally: await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        # But simple call for startup is usually fine if DB is fast.
        command.upgrade(alembic_cfg, "head")
        print("✅ Alembic migrations applied successfully.")
        
    except Exception as e:
        print(f"❌ Failed to run Alembic migrations: {e}")
        # Note: We might NOT want to stop the app here if it's just a non-critical warning,
        # but schema mismatch is usually critical. 
        # For now, we print and continue, hoping create_tables catches basics 
        # (though create_tables doesn't alter tables).


    create_tables()
    
    redis_connected = await redis_cache.init_redis()
    if not redis_connected:
        print("⚠️ سنتحدث بدون كاش Redis")
    else:
        print("✅ Redis cache initialized successfully")
    
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    
    @scheduler.scheduled_job('cron', hour=13, minute=0) # 13:00 UTC = 17:00 UAE Time
    async def daily_rs_update():
        from scripts.daily_market_update import update_daily
        print("🔄 Running daily RS update (Scraper V2 + RS V2)...")
        # تشغيل السكريبت المتزامن في Thread منفصل عشان مياخدش الـ Thread الأساسي
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, update_daily)
    
    scheduler.start()
    print("✅ Scheduler started for daily RS updates (At 13:00 UTC / 17:00 UAE)")

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