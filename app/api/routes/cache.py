from fastapi import APIRouter, HTTPException, Query
from app.core.redis import redis_cache
from app.services.cache.stock_cache import stock_cache
from app.services.cache.financial_cache import financial_cache
import asyncio

router = APIRouter(prefix="/cache", tags=["Cache Management"])

@router.post("/clear/all")
async def clear_all_cache():
    """مسح كل الكاش"""
    try:
        await redis_cache.flush_all()
        await stock_cache.clear_all_cache()
        return {"message": "✅ تم مسح كل الكاش بنجاح"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في مسح الكاش: {str(e)}")

@router.post("/clear/stocks")
async def clear_stocks_cache():
    """مسح كاش الأسهم"""
    try:
        await stock_cache.clear_all_cache()
        return {"message": "✅ تم مسح كاش الأسهم بنجاح"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في مسح كاش الأسهم: {str(e)}")

@router.post("/clear/financials")
async def clear_financial_cache(
    symbol: str = Query(None, description="رمز سهم واحد أو رموز متعددة مفصولة بفواصل")
):
    """مسح كاش البيانات المالية لرمز أو رموز محددة"""
    try:
        result = await financial_cache.clear_financial_cache(symbol)
        
        if symbol:
            if ',' in symbol:
                symbol_list = [s.strip() for s in symbol.split(',')]
                message = f"✅ تم مسح كاش البيانات المالية لـ {len(symbol_list)} رمز"
            else:
                message = f"✅ تم مسح كاش البيانات المالية لـ {symbol}"
        else:
            message = "✅ تم مسح كاش البيانات المالية بالكامل"
            
        return {"message": message, "deleted_count": result}
    except Exception as e:
        print(f"❌ خطأ في مسح كاش البيانات المالية: {e}")
        # إرجاع رسالة خطأ أكثر وضوحاً
        error_detail = f"خطأ في مسح كاش البيانات المالية: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

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

@router.delete("/clear/symbols")
async def clear_specific_symbols_cache(
    symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل"),
    clear_db: bool = Query(False, description="مسح من قاعدة البيانات أيضاً")
):
    """مسح كاش رموز محددة"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        cleared_count = 0
        for symbol in symbol_list:
            clean_sym = ''.join(filter(str.isdigit, symbol)).upper()
            
            # مسح من Redis للأسهم
            cache_key = f"tadawul_stocks:symbol:{clean_sym}:country:Saudi Arabia"
            await redis_cache.delete(cache_key)
            
            # مسح كاش البيانات المالية
            await financial_cache.clear_financial_cache(clean_sym)
            
            # مسح من قاعدة البيانات إذا طلب
            if clear_db:
                from app.core.database import get_db
                db = next(get_db())
                try:
                    from app.models.profile import CompanyProfile
                    from app.models.quote import StockQuote
                    from app.models.financials import IncomeStatement, BalanceSheet, CashFlow
                    
                    # حذف من Profile
                    db.query(CompanyProfile).filter(CompanyProfile.symbol == clean_sym).delete()
                    # حذف من Quote
                    db.query(StockQuote).filter(StockQuote.symbol == clean_sym).delete()
                    # حذف البيانات المالية
                    db.query(IncomeStatement).filter(IncomeStatement.symbol == clean_sym).delete()
                    db.query(BalanceSheet).filter(BalanceSheet.symbol == clean_sym).delete()
                    db.query(CashFlow).filter(CashFlow.symbol == clean_sym).delete()
                    
                    db.commit()
                    print(f"🗑️ تم حذف بيانات {clean_sym} من PostgreSQL")
                except Exception as e:
                    print(f"⚠️ خطأ في حذف {clean_sym} من PostgreSQL: {e}")
                    db.rollback()
                finally:
                    db.close()
            
            cleared_count += 1
            print(f"🧹 تم مسح كاش {clean_sym}")
        
        return {
            "message": f"✅ تم مسح كاش {cleared_count} رمز",
            "cleared_symbols": symbol_list,
            "clear_db": clear_db
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في مسح الكاش: {str(e)}")

@router.get("/stats")
async def cache_stats():
    """إحصائيات الكاش"""
    try:
        # جلب كل مفاتيح الـ stocks
        stock_keys = await redis_cache.keys("tadawul_stocks:*")
        financial_keys = await redis_cache.keys("financials:*")
        
        # تصنيف المفاتيح
        symbol_keys = [k for k in stock_keys if "symbol:" in k]
        bulk_keys = [k for k in stock_keys if "bulk:" in k]
        page_keys = [k for k in stock_keys if "page:" in k]
        all_keys = [k for k in stock_keys if "all:" in k]
        
        # مفاتيح البيانات المالية
        income_keys = [k for k in financial_keys if "income:" in k]
        balance_keys = [k for k in financial_keys if "balance:" in k]
        cashflow_keys = [k for k in financial_keys if "cashflow:" in k]
        
        return {
            "total_stock_keys": len(stock_keys),
            "symbol_keys": len(symbol_keys),
            "bulk_keys": len(bulk_keys),
            "page_keys": len(page_keys),
            "all_keys": len(all_keys),
            "total_financial_keys": len(financial_keys),
            "income_keys": len(income_keys),
            "balance_keys": len(balance_keys),
            "cashflow_keys": len(cashflow_keys),
            "sample_stock_keys": stock_keys[:3],
            "sample_financial_keys": financial_keys[:3]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في جلب إحصائيات الكاش: {str(e)}")

@router.post("/refresh/symbols")
async def refresh_symbols_cache(
    symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل")
):
    """إعادة جلب بيانات رموز محددة من API"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        refreshed_count = 0
        for symbol in symbol_list:
            clean_sym = ''.join(filter(str.isdigit, symbol)).upper()
            
            # مسح الكاش أولاً
            cache_key = f"tadawul_stocks:symbol:{clean_sym}:country:Saudi Arabia"
            await redis_cache.delete(cache_key)
            
            # مسح كاش البيانات المالية
            await financial_cache.clear_financial_cache(clean_sym)
            
            # ثم جلب البيانات من جديد (سيتم حفظها تلقائياً)
            stock_data = await stock_cache.get_stock_by_symbol(clean_sym, "Saudi Arabia")
            
            if stock_data:
                refreshed_count += 1
                print(f"🔄 تم إعادة جلب بيانات {clean_sym}")
            else:
                print(f"⚠️ فشل في جلب بيانات {clean_sym}")
        
        return {
            "message": f"✅ تم إعادة جلب بيانات {refreshed_count} رمز",
            "refreshed_symbols": refreshed_count,
            "total_requested": len(symbol_list)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في إعادة جلب البيانات: {str(e)}")

@router.post("/refresh/financials")
async def refresh_financials_cache(
    symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل"),
    period: str = Query("annual", description="الفترة: annual أو quarterly")
):
    """إعادة جلب البيانات المالية لرموز محددة"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        refreshed_count = 0
        for symbol in symbol_list:
            clean_sym = ''.join(filter(str.isdigit, symbol)).upper()
            
            # مسح كاش البيانات المالية أولاً
            await financial_cache.clear_financial_cache(clean_sym)
            
            # ثم جلب البيانات من جديد
            try:
                income_data = await financial_cache.get_income_statement(clean_sym, period)
                balance_data = await financial_cache.get_balance_sheet(clean_sym, period)
                cashflow_data = await financial_cache.get_cash_flow(clean_sym, period)
                
                if income_data.get('income_statement') or balance_data.get('balance_sheet') or cashflow_data.get('cash_flow'):
                    refreshed_count += 1
                    print(f"🔄 تم إعادة جلب البيانات المالية لـ {clean_sym}")
                else:
                    print(f"⚠️ لا توجد بيانات مالية لـ {clean_sym}")
                    
            except Exception as e:
                print(f"❌ خطأ في جلب البيانات المالية لـ {clean_sym}: {e}")
        
        return {
            "message": f"✅ تم إعادة جلب البيانات المالية لـ {refreshed_count} رمز",
            "refreshed_symbols": refreshed_count,
            "total_requested": len(symbol_list),
            "period": period
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطأ في إعادة جلب البيانات المالية: {str(e)}")