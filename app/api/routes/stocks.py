from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import update

# ⭐ استيرادات واضحة

from app.services.rs_rating import calculate_all_rs_ratings
from app.core.redis import redis_cache
from app.core.database import get_db


router = APIRouter(prefix="/stocks", tags=["Tadawul Stocks"])

# ============ الـ Endpoints الرئيسية ============

@router.get("/saudi/bulk")
async def get_all_saudi_stocks(country: str = Query("Saudi Arabia")):
    """
    جلب كل الأسهم السعودية مع RS Ratings
    """
    try:
        return await stock_cache.get_all_saudi_stocks(country)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate-rs")
async def calculate_rs_endpoint(background_tasks: BackgroundTasks, country: str = Query("Saudi Arabia")):
    """
    🎯 بدء حساب RS Ratings لجميع الأسهم
    """
    try:
        stocks_data = await stock_cache.get_all_saudi_stocks(country)
        symbols = [stock["symbol"] for stock in stocks_data.get("data", [])]
        
        if not symbols:
            raise HTTPException(status_code=404, detail="No stocks found")
        
        batch_size = 20
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            print(f"🎯 Processing batch {i//batch_size + 1}: {len(batch)} symbols")
            background_tasks.add_task(calculate_and_save_rs_task, batch)
        
        print(f"🎯 Starting RS calculation for {len(symbols)} symbols...")
        background_tasks.add_task(calculate_and_save_rs_task, symbols)
        
        return {
            "success": True,
            "message": "RS calculation started (Excel formula method)",
            "symbols_count": len(symbols),
            "batches": (len(symbols) + batch_size - 1) // batch_size
        }
    
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{symbol}")
async def get_single_stock(symbol: str, country: str = Query("Saudi Arabia")):
    """
    جلب سهم واحد مع RS Ratings
    """
    try:
        stock = await stock_cache.get_stock_data(symbol, country)
        if not stock:
            raise HTTPException(status_code=404, detail="Stock not found")
        return stock
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ دالة الخلفية ============


# app/api/stocks.py

# ... (الكود السابق يبقى كما هو) ...

async def calculate_and_save_rs_task(symbols: List[str]):
    """
    دالة خلفية لحساب RS وChange% وحفظهما في DB وRedis
    """
    print(f"🔄 Starting RS & Change calculation for {len(symbols)} symbols...")
    
    try:
        # ⭐ حساب RS و Change معاً
        rs_data = await calculate_all_rs_ratings(symbols)
        
        if not rs_data:
            print("❌ No RS data calculated")
            return
        
        print(f"✅ RS & Change calculated for {len(rs_data)} stocks")
        
        db: Session = next(get_db())
        
        try:
            updated_count = 0
            
            for symbol, scores in rs_data.items():
                try:
                    quote = db.query(StockQuote).filter(StockQuote.symbol == symbol).first()
                    
                    if quote:
                        # حفظ RS Ratings
                        if scores.get('rs_12m') is not None:
                            quote.rs_12m = scores['rs_12m']
                        if scores.get('rs_9m') is not None:
                            quote.rs_9m = scores['rs_9m']
                        if scores.get('rs_6m') is not None:
                            quote.rs_6m = scores['rs_6m']
                        if scores.get('rs_3m') is not None:
                            quote.rs_3m = scores['rs_3m']
                        if scores.get('rs_1m') is not None:
                            quote.rs_1m = scores['rs_1m']
                        if scores.get('rs_2w') is not None:
                            quote.rs_2w = scores['rs_2w']
                        if scores.get('rs_1w') is not None:
                            quote.rs_1w = scores['rs_1w']
                        
                        # ⭐ حفظ Change%
                        if scores.get('change_12m') is not None:
                            quote.change_12m = scores['change_12m']
                        if scores.get('change_9m') is not None:
                            quote.change_9m = scores['change_9m']
                        if scores.get('change_6m') is not None:
                            quote.change_6m = scores['change_6m']
                        if scores.get('change_3m') is not None:
                            quote.change_3m = scores['change_3m']
                        if scores.get('change_1m') is not None:
                            quote.change_1m = scores['change_1m']
                        if scores.get('change_2w') is not None:
                            quote.change_2w = scores['change_2w']
                        if scores.get('change_1w') is not None:
                            quote.change_1w = scores['change_1w']
                        
                        updated_count += 1
                
                except Exception as e:
                    print(f"⚠️ Error updating {symbol}: {e}")
                    continue
            
            db.commit()
            print(f"✅ Saved RS & Change ratings to DB for {updated_count} stocks")
            
        except Exception as e:
            db.rollback()
            print(f"❌ Database error: {e}")
            return
        finally:
            db.close()
        
        # مسح الكاش
        try:
            await redis_cache.delete("tadawul:all:Saudi Arabia")
            print("✅ Cleared Redis cache")
        except Exception as e:
            print(f"⚠️ Could not clear Redis cache: {e}")
        
        print("🎉 RS & Change calculation task completed")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")


# ============ Endpoints إضافية ============

@router.delete("/delete-symbols")
async def delete_symbols(
    symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل. مثال: 1010,1020,1030"),
    clear_from: str = Query("redis", description="من أين تريد الحذف؟ redis | db | both"),
    confirm_db_delete: bool = Query(False, description="⚠️ تأكيد الحذف من DB (خطير!)")
):
    """
    🗑️ حذف بيانات رموز محددة من Redis و/أو Database
    
    ملاحظات أمان:
    - الحذف من Redis آمن وسريع
    - الحذف من DB خطير جداً ويتطلب confirm_db_delete=true
    - يحذف السجل الكامل inclucing RS columns
    - بعد الحذف، الكاش الكلي "all" يتم مسحه تلقائياً
    """
    
    if clear_from not in ["redis", "db", "both"]:
        raise HTTPException(status_code=400, detail="clear_from يجب أن يكون: redis, db, أو both")
    
    if clear_from in ["db", "both"] and not confirm_db_delete:
        raise HTTPException(
            status_code=403, 
            detail="⚠️ لحذف من DB، يجب إضافة confirm_db_delete=true"
        )
    
    symbol_list = [clean_symbol(s.strip()) for s in symbols.split(",")]
    results = []
    db = next(get_db())
    
    try:
        for symbol in symbol_list:
            result = {"symbol": symbol, "redis_deleted": False, "db_deleted": False, "error": None}
            
            # 1️⃣ حذف من Redis
            if clear_from in ["redis", "both"]:
                cache_key = f"tadawul:stock:{symbol}:Saudi Arabia"
                try:
                    deleted = await redis_cache.delete(cache_key)
                    result["redis_deleted"] = bool(deleted)
                    print(f"🗑️ Redis: {symbol} {'deleted' if deleted else 'not found'}")
                except Exception as e:
                    result["error"] = f"Redis Error: {str(e)}"
            
            # 2️⃣ حذف من Database (يحذف السجل الكامل inclucing RS)
            if clear_from in ["db", "both"]:
                try:
                    profile_deleted = db.query(CompanyProfile).filter(CompanyProfile.symbol == symbol).delete()
                    quote_deleted = db.query(StockQuote).filter(StockQuote.symbol == symbol).delete()
                    
                    if profile_deleted or quote_deleted:
                        result["db_deleted"] = True
                        db.commit()
                        print(f"🗑️ DB: {symbol} deleted (profile={profile_deleted}, quote={quote_deleted})")
                    else:
                        db.commit()
                        print(f"🗑️ DB: {symbol} not found")
                        
                except Exception as e:
                    db.rollback()
                    result["error"] = f"DB Error: {str(e)}"
            
            results.append(result)
        
        # 3️⃣ مسح الكاش الكلي "all"
        if clear_from in ["redis", "both"]:
            await redis_cache.delete("tadawul:all:Saudi Arabia")
            print("🗑️ Redis: cleared 'all' cache")
        
        total_deleted = sum(1 for r in results if r["redis_deleted"] or r["db_deleted"])
        
        return {
            "success": True,
            "message": f"تم حذف بيانات {total_deleted} رمز من {len(symbol_list)}",
            "clear_from": clear_from,
            "total_requested": len(symbol_list),
            "total_deleted": total_deleted,
            "details": results
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"خطأ عام: {str(e)}")
    
    finally:
        db.close()

# ============ 🎯 Endpoint جديد مخصص لمسح RS فقط ============

@router.delete("/clear-rs")
async def clear_rs_data(
    symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل. مثال: 1010,1020,1030"),
    clear_from: str = Query("db", description="من أين تريد مسح RS؟ db | redis | both")
):
    """
    🎯 مسح بيانات RS فقط (تفريغ الأعمدة) مع الحفاظ على بيانات السهم الأساسية
    
    ملاحظات:
    - db: يعيد قيم RS إلى NULL في PostgreSQL (UPDATE not DELETE)
    - redis: يمسح الكاش (سيتم إعادة الحساب تلقائياً عند الجلب التالي)
    - both: يفعل الاثنين معاً
    - هذا لا يحذف السجل، فقط يمسح أعمدة RS
    """
    
    if clear_from not in ["db", "redis", "both"]:
        raise HTTPException(status_code=400, detail="clear_from يجب أن يكون: db, redis, أو both")
    
    symbol_list = [clean_symbol(s.strip()) for s in symbols.split(",")]
    results = []
    db = next(get_db())
    
    try:
        for symbol in symbol_list:
            result = {"symbol": symbol, "db_cleared": False, "redis_cleared": False, "error": None}
            
            # 1️⃣ مسح من Database (تعيين RS columns إلى NULL)
            if clear_from in ["db", "both"]:
                try:
                    stmt = (
                        update(StockQuote)
                        .where(StockQuote.symbol == symbol)
                        .values(
                            rs_12m=None,
                            rs_9m=None,
                            rs_6m=None,
                            rs_3m=None,
                            rs_1m=None,
                            rs_2w=None,
                            rs_1w=None
                        )
                    )
                    db.execute(stmt)
                    db.commit()
                    result["db_cleared"] = True
                    print(f"✅ RS cleared in DB for {symbol}")
                except Exception as e:
                    db.rollback()
                    result["error"] = f"DB Error: {str(e)}"
            
            # 2️⃣ مسح من Redis
            if clear_from in ["redis", "both"]:
                try:
                    cache_key = f"tadawul:stock:{symbol}:Saudi Arabia"
                    await redis_cache.delete(cache_key)
                    result["redis_cleared"] = True
                    print(f"✅ RS cache cleared for {symbol}")
                except Exception as e:
                    result["error"] = f"Redis Error: {str(e)}"
            
            results.append(result)
        
        # 3️⃣ مسح الكاش الكلي "all"
        await redis_cache.delete("tadawul:all:Saudi Arabia")
        print("✅ Cleared Redis 'all' cache")
        
        total_cleared = sum(1 for r in results if r["db_cleared"] or r["redis_cleared"])
        
        return {
            "success": True,
            "message": f"تم مسح RS لـ {total_cleared} رمز من {len(symbol_list)}",
            "clear_from": clear_from,
            "total_requested": len(symbol_list),
            "total_cleared": total_cleared,
            "details": results
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"خطأ عام: {str(e)}")
    
    finally:
        db.close()

@router.delete("/clear-redis")
async def clear_redis_cache(
    pattern: str = Query("tadawul:*", description="نمط المفاتيح للمسح. افتراضي: tadawul:*")
):
    """
    🗑️ مسح جميع مفاتيح Redis المتعلقة بالأسهم
    """
    try:
        keys = await redis_cache.keys(pattern)
        
        if not keys:
            return {"success": True, "message": "لم يتم العثور على مفاتيح مطابقة", "deleted_count": 0}
        
        deleted_count = 0
        for key in keys:
            deleted = await redis_cache.delete(key)
            deleted_count += deleted
        
        print(f"🗑️ Redis: deleted {deleted_count} keys matching '{pattern}'")
        
        return {
            "success": True,
            "message": f"تم مسح {deleted_count} مفتاح Redis",
            "pattern": pattern,
            "deleted_keys": keys
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في مسح Redis: {str(e)}")
    
@router.get("/{symbol}/name")
async def get_company_name(
    symbol: str,
    country: str = Query("Saudi Arabia")
):
    """
    جلب اسم الشركة من قاعدة البيانات (مع التصحيحات)
    """
    try:
        clean_sym = clean_symbol(symbol)
        
        # استخدام stock_cache للحصول على البيانات (الذي يستخدم DB أولاً)
        stock_data = await stock_cache.get_stock_data(clean_sym, country)
        
        if not stock_data:
            raise HTTPException(status_code=404, detail="Stock not found")
            
        return {
            "symbol": clean_sym,
            "name": stock_data.get("name", clean_sym),
            "country": country
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    





    
