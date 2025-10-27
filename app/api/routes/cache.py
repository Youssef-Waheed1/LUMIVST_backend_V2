from fastapi import APIRouter, HTTPException
from app.core.redis import redis_cache
from app.services.cache.company_cache import company_cache
from app.services.cache.financial_cache import financial_cache

router = APIRouter(prefix="/cache", tags=["Cache Management"])

@router.post("/clear/all")
async def clear_all_cache():
    """مسح كل الكاش"""
    try:
        await redis_cache.flush_all()
        return {"message": "✅ تم مسح كل الكاش بنجاح"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في مسح الكاش: {str(e)}")

@router.post("/clear/companies")
async def clear_companies_cache():
    """مسح كاش الشركات"""
    try:
        await company_cache.clear_companies_cache()
        return {"message": "✅ تم مسح كاش الشركات بنجاح"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في مسح كاش الشركات: {str(e)}")

@router.post("/clear/financials")
async def clear_financial_cache(symbol: str = None):
    """مسح كاش البيانات المالية"""
    try:
        await financial_cache.clear_financial_cache(symbol)
        message = f"✅ تم مسح كاش البيانات المالية لـ {symbol}" if symbol else "✅ تم مسح كاش البيانات المالية"
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في مسح كاش البيانات المالية: {str(e)}")

@router.get("/status")
async def cache_status():
    """الحصول على حالة الكاش"""
    try:
        # اختبار اتصال Redis
        is_connected = redis_cache.redis_client is not None
        if is_connected:
            try:
                await redis_cache.redis_client.ping()
                status = "connected"
            except:
                status = "disconnected"
        else:
            status = "disconnected"
        
        return {
            "redis_status": status,
            "message": "✅ نظام الكاش يعمل بشكل طبيعي" if status == "connected" else "❌ نظام الكاش غير متاح"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في التحقق من حالة الكاش: {str(e)}")