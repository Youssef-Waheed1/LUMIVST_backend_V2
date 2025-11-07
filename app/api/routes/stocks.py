from fastapi import APIRouter, HTTPException, Query
from app.services.cache.stock_cache import stock_cache,SAUDI_STOCKS 
from app.schemas.stock import StockListResponse, StockResponse 
from app.services.cache.stock_cache import SAUDI_STOCKS 
from app.core.database import get_db

router = APIRouter(prefix="/api/stocks", tags=["Tadawul Stocks"])

@router.get("/saudi/bulk", response_model=StockListResponse)
async def get_all_saudi_stocks_bulk(
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")
):
    
    """جلب كل الأسهم السعودية المحددة في SAUDI_STOCKS مرة واحدة"""
    try:
        result = await stock_cache.get_all_saudi_stocks(country)
        return result
    except Exception as e:
        print(f"❌ خطأ في جلب الأسهم السعودية: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/bulk", response_model=StockListResponse)
async def get_bulk_stocks(
    symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل"),
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")
):
    """جلب بيانات مجموعة من الرموز مرة واحدة"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        if len(symbol_list) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 symbols allowed")
        
        result = await stock_cache.get_bulk_stocks_data(symbol_list, country)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ خطأ في جلب البيانات المجمعة: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("", response_model=StockListResponse)
async def get_tadawul_stocks(
    all: bool = Query(False, description="جلب كل الأسهم بدون pagination"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(25, ge=1, le=1000, description="Items per page (max: 1000)"),
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")  #  جديد
):
    """جلب قائمة أسهم Tadawul مع البيانات المالية"""
    try:
        if all:
            result = await stock_cache.get_all_stocks() 
        else:
            result = await stock_cache.get_stocks(page=page, limit=limit) 
        return result
    except Exception as e:
        print(f"❌ خطأ في جلب أسهم Tadawul: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{symbol}", response_model=StockResponse)
async def get_tadawul_stock_by_symbol(
    symbol: str,
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")  #  جديد
):
    """جلب بيانات سهم معين من Tadawul"""
    try:
        stock = await stock_cache.get_stock_by_symbol(symbol) 
        
        if not stock:
            raise HTTPException(status_code=404, detail=f"Tadawul stock '{symbol}' not found")
        
        return stock
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ خطأ في جلب سهم Tadawul: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.get("/verify/symbols")
async def verify_saudi_symbols(
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")  #  جديد
):
    """التحقق من صحة الرموز السعودية"""
    try:
        from app.services.cache.stock_cache import get_filtered_saudi_stocks
        
        verified_stocks = await get_filtered_saudi_stocks()
        
        return {
            "verified_count": len(verified_stocks),
            "total_count": len(SAUDI_STOCKS),
            "verified_stocks": verified_stocks,
            "invalid_stocks": {k: v for k, v in SAUDI_STOCKS.items() if k not in verified_stocks}
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في التحقق من الرموز: {str(e)}")
    
@router.get("/db/stats")
async def get_database_stats(
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")  #  جديد
):
    """الحصول على إحصائيات قاعدة البيانات"""
    try:
        db = next(get_db())
        
        from app.models.profile import CompanyProfile
        from app.models.quote import StockQuote
        
        profile_count = db.query(CompanyProfile).count()
        quote_count = db.query(StockQuote).count()
        
        # أحدث 5 شركات
        latest_profiles = db.query(CompanyProfile).order_by(CompanyProfile.updated_at.desc()).limit(5).all()
        latest_companies = [
            {
                "symbol": p.symbol,
                "name": p.name,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            }
            for p in latest_profiles
        ]
        
        return {
            "profiles_count": profile_count,
            "quotes_count": quote_count,
            "latest_companies": latest_companies,
            "database_status": "connected" if profile_count >= 0 else "disconnected"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب إحصائيات قاعدة البيانات: {str(e)}")