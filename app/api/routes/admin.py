from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.redis import redis_cache

from app.core.database import get_db
from app.services.cache.stock_cache import stock_cache 
from app.models.user import User
from app.schemas.auth import UserResponse
from app.api.deps import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0, 
    limit: int = 100, 
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """عرض قائمة المستخدمين (للمدير فقط)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """حذف مستخدم معين (للمدير فقط)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    
    # Optional: Prevent deleting self?
    if user.id == current_admin.id:
         raise HTTPException(status_code=400, detail="لا يمكنك حذف حسابك الخاص من هنا")

    db.delete(user)
    db.commit()
    return {"message": f"تم حذف المستخدم {user.email} بنجاح"}

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