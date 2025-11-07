from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.cache.stock_cache import stock_cache 

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/refresh-data")
async def refresh_stock_data(page: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    """إجبار النظام على تحديث البيانات من API"""
    try:
        # مسح الكاش أولاً
        await stock_cache.clear_all_cache() 
        
        # جلب بيانات جديدة من API
        api_data = await stock_cache.get_stocks(page=page, limit=limit) 
        
        if api_data and api_data.get("data"):
            return {
                "message": f"✅ تم تحديث بيانات {len(api_data['data'])} سهم",
                "stocks_updated": len(api_data["data"]), 
                "page": page,
                "limit": limit
            }
        else:
            raise HTTPException(status_code=500, detail="❌ فشل في جلب البيانات من API")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ خطأ في تحديث البيانات: {str(e)}")

@router.get("/stats")
async def get_system_stats(db: Session = Depends(get_db)):
    """إحصائيات النظام"""
    try:
        # جلب إحصائيات من الـ cache
        all_stocks_data = await stock_cache.get_all_stocks() 
        total_stocks = all_stocks_data.get("total", 0) 
        
        # جلب إحصائيات من قاعدة البيانات لو محتاج
        db_stats = {
            "total_stocks": total_stocks,
            "database": "PostgreSQL",
            "cache": "Redis", 
            "data_source": "TwelveData API (Profile + Quote)",
            "cache_strategy": "Redis → PostgreSQL → API"
        }
        
        return db_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ خطأ في جلب إحصائيات النظام: {str(e)}")

@router.post("/force-api-refresh/{symbol}")
async def force_api_refresh(symbol: str):
    """إجبار تحديث بيانات سهم معين من API"""
    try:
        # مسح كاش السهم المحدد
        cache_key = f"tadawul_stocks:symbol:{symbol}"
        await redis_cache.delete(cache_key)
        
        # جلب بيانات جديدة من API
        stock_data = await stock_cache.get_stock_by_symbol(symbol) 
        
        if stock_data:
            return {
                "message": f"✅ تم تحديث بيانات السهم {symbol} بنجاح",
                "symbol": symbol,
                "name": stock_data.get("name"),
                "price": stock_data.get("price")
            }
        else:
            raise HTTPException(status_code=404, detail=f"❌ لم يتم العثور على السهم {symbol}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ خطأ في تحديث بيانات السهم: {str(e)}")