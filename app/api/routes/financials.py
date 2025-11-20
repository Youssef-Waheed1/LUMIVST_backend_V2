from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import json
from app.core.database import get_db
from app.models.financials import IncomeStatement, BalanceSheet, CashFlow
from app.services.cache.financial_cache import financial_cache

router = APIRouter(prefix="/financials", tags=["Financials"])


#  إضافة route جديد لجلب البيانات من قاعدة البيانات المحلية
@router.get("/{symbol}")
async def get_financial_data_from_db(
    symbol: str,
    country: str = Query("Saudi Arabia", description="البلد"),
    period: str = Query("annual", regex="^(annual|quarterly)$", description="الفترة: annual or quarterly"),
    db: Session = Depends(get_db)
):
    """
    جلب البيانات المالية من قاعدة البيانات المحلية
    """
    try:
        print(f"📊 جلب البيانات المالية من قاعدة البيانات لـ {symbol} - {country} - {period}")
        
        # بناء الاستعلام بناءً على الفترة
        if period == "annual":
            # البيانات السنوية (بدون quarter)
            income_filter = IncomeStatement.quarter.is_(None)
            balance_filter = BalanceSheet.quarter.is_(None)
            cashflow_filter = CashFlow.quarter.is_(None)
        else:
            # البيانات الربع سنوية (مع quarter)
            income_filter = IncomeStatement.quarter.isnot(None)
            balance_filter = BalanceSheet.quarter.isnot(None)
            cashflow_filter = CashFlow.quarter.isnot(None)
        
        # جلب البيانات من قاعدة البيانات
        income_data = db.query(IncomeStatement).filter(
            IncomeStatement.symbol == symbol,
            IncomeStatement.country == country,
            income_filter
        ).order_by(IncomeStatement.fiscal_date.desc()).limit(6).all()
        
        balance_data = db.query(BalanceSheet).filter(
            BalanceSheet.symbol == symbol,
            BalanceSheet.country == country,
            balance_filter
        ).order_by(BalanceSheet.fiscal_date.desc()).limit(6).all()
        
        cashflow_data = db.query(CashFlow).filter(
            CashFlow.symbol == symbol,
            CashFlow.country == country,
            cashflow_filter
        ).order_by(CashFlow.fiscal_date.desc()).limit(6).all()
        
        print(f"📈 نتائج الجلب: دخل={len(income_data)}, ميزانية={len(balance_data)}, تدفقات={len(cashflow_data)}")
        
        # دالة لتحويل البيانات إلى JSON
        def serialize_item(item):
            result = {}
            for column in item.__table__.columns:
                value = getattr(item, column.name)
                # تحويل datetime إلى string
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
            return result
        
        response_data = {
            "income_statement": [serialize_item(item) for item in income_data],
            "balance_sheet": [serialize_item(item) for item in balance_data],
            "cash_flow": [serialize_item(item) for item in cashflow_data],
            "meta": {
                "symbol": symbol,
                "country": country,
                "period": period,
                "records_count": {
                    "income": len(income_data),
                    "balance": len(balance_data),
                    "cash_flow": len(cashflow_data)
                }
            }
        }
        
        return response_data
        
    except Exception as e:
        print(f"❌ خطأ في جلب البيانات من قاعدة البيانات: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في جلب البيانات: {str(e)}")


@router.get("/income_statement/{symbol}")
async def income_statement(
    symbol: str,
    country: str = Query("Saudi Arabia", description="البلد (مثل: Saudi Arabia, UAE, Egypt)"),
    period: str = Query("annual", regex="^(annual|quarterly)$", description="الفترة: annual or quarterly"),
    limit: int = Query(6, ge=1, le=20, description="عدد الفترات المطلوبة (1-20)")
):
    try:
        print(f"📈 طلب قائمة الدخل: {symbol} - البلد: {country} - الفترة: {period}")
        
        # استخدام البلد والرمز معاً كمفتاح فريد
        cache_key = f"{country}:{symbol}"
        data = await financial_cache.get_income_statement(cache_key, period=period, limit=limit)
        
        # تأكد من أن البيانات في التنسيق الصحيح
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {"income_statement": []}
        
        if not data.get('income_statement'):
            print(f"⚠️ لا توجد بيانات دخل لـ {symbol} في {country}")
            data = {"income_statement": []}
            
        return data
    except Exception as e:
        print(f"❌ خطأ في قائمة الدخل لـ {symbol}: {e}")
        return {"income_statement": []}

@router.get("/balance_sheet/{symbol}")
async def balance_sheet(
    symbol: str,
    country: str = Query("Saudi Arabia", description="البلد (مثل: Saudi Arabia, UAE, Egypt)"),
    period: str = Query("annual", regex="^(annual|quarterly)$", description="الفترة: annual or quarterly"),
    limit: int = Query(6, ge=1, le=20, description="عدد الفترات المطلوبة (1-20)")
):
    try:
        print(f"📊 طلب الميزانية العمومية: {symbol} - البلد: {country} - الفترة: {period}")
        
        cache_key = f"{country}:{symbol}"
        data = await financial_cache.get_balance_sheet(cache_key, period=period, limit=limit)
        
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {"balance_sheet": []}
        
        if not data.get('balance_sheet'):
            print(f"⚠️ لا توجد بيانات ميزانية لـ {symbol} في {country}")
            data = {"balance_sheet": []}
            
        return data
    except Exception as e:
        print(f"❌ خطأ في الميزانية العمومية لـ {symbol}: {e}")
        return {"balance_sheet": []}

@router.get("/cash_flow/{symbol}")
async def cash_flow(
    symbol: str,
    country: str = Query("Saudi Arabia", description="البلد (مثل: Saudi Arabia, UAE, Egypt)"),
    period: str = Query("annual", regex="^(annual|quarterly)$", description="الفترة: annual or quarterly"),
    limit: int = Query(6, ge=1, le=20, description="عدد الفترات المطلوبة (1-20)")
):
    try:
        print(f"💰 طلب التدفقات النقدية: {symbol} - البلد: {country} - الفترة: {period}")
        
        cache_key = f"{country}:{symbol}"
        data = await financial_cache.get_cash_flow(cache_key, period=period, limit=limit)
        
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {"cash_flow": []}
        
        if not data.get('cash_flow'):
            print(f"⚠️ لا توجد بيانات تدفقات نقدية لـ {symbol} في {country}")
            data = {"cash_flow": []}
            
        return data
    except Exception as e:
        print(f"❌ خطأ في التدفقات النقدية لـ {symbol}: {e}")
        return {"cash_flow": []}

# @router.post("/load/{symbol}")
# async def load_financial_data(
#     symbol: str,
#     country: str = Query("Saudi Arabia", description="البلد"),
#     period: str = Query("annual", regex="^(annual|quarterly)$"),
#     limit: int = Query(6, ge=1, le=20)
# ):
#     """جلب وتخزين البيانات المالية لرمز معين"""
#     try:
#         print(f"🔄 بدء تحميل البيانات المالية لـ {symbol} - البلد: {country}")
        
#         cache_key = f"{country}:{symbol}"
        
#         # جلب البيانات المالية (سيتم تخزينها تلقائياً في الكاش وقاعدة البيانات)
#         income_data = await financial_cache.get_income_statement(cache_key, period, limit)
#         balance_data = await financial_cache.get_balance_sheet(cache_key, period, limit)
#         cashflow_data = await financial_cache.get_cash_flow(cache_key, period, limit)
        
#         # التحقق من وجود البيانات
#         has_income = bool(income_data.get('income_statement'))
#         has_balance = bool(balance_data.get('balance_sheet'))
#         has_cashflow = bool(cashflow_data.get('cash_flow'))
        
#         return {
#             "message": f"✅ تم تحميل البيانات المالية لـ {symbol} في {country}",
#             "symbol": symbol,
#             "country": country,
#             "period": period,
#             "data_available": {
#                 "income_statement": has_income,
#                 "balance_sheet": has_balance,
#                 "cash_flow": has_cashflow
#             },
#             "records_count": {
#                 "income": len(income_data.get('income_statement', [])),
#                 "balance": len(balance_data.get('balance_sheet', [])),
#                 "cash_flow": len(cashflow_data.get('cash_flow', []))
#             }
#         }
        
#     except Exception as e:
#         print(f"❌ خطأ في تحميل البيانات المالية لـ {symbol}: {e}")
#         raise HTTPException(status_code=500, detail=f"خطأ في تحميل البيانات المالية: {str(e)}")

# @router.post("/load/bulk")
# async def load_bulk_financial_data(
#     symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل"),
#     country: str = Query("Saudi Arabia", description="البلد"),
#     period: str = Query("annual", regex="^(annual|quarterly)$"),
#     limit: int = Query(6, ge=1, le=20)
# ):
#     """جلب وتخزين البيانات المالية لرموز متعددة"""
#     try:
#         symbol_list = [s.strip() for s in symbols.split(',')]
#         results = []
        
#         print(f"🔄 بدء تحميل البيانات المالية لـ {len(symbol_list)} رمز في {country}...")
        
#         for symbol in symbol_list:
#             try:
#                 cache_key = f"{country}:{symbol}"
                
#                 # جلب البيانات المالية
#                 income_data = await financial_cache.get_income_statement(cache_key, period, limit)
#                 balance_data = await financial_cache.get_balance_sheet(cache_key, period, limit)
#                 cashflow_data = await financial_cache.get_cash_flow(cache_key, period, limit)
                
#                 # التحقق من وجود البيانات
#                 has_income = bool(income_data.get('income_statement'))
#                 has_balance = bool(balance_data.get('balance_sheet'))
#                 has_cashflow = bool(cashflow_data.get('cash_flow'))
                
#                 results.append({
#                     "symbol": symbol,
#                     "country": country,
#                     "success": True,
#                     "data_available": {
#                         "income_statement": has_income,
#                         "balance_sheet": has_balance,
#                         "cash_flow": has_cashflow
#                     },
#                     "records_count": {
#                         "income": len(income_data.get('income_statement', [])),
#                         "balance": len(balance_data.get('balance_sheet', [])),
#                         "cash_flow": len(cashflow_data.get('cash_flow', []))
#                     }
#                 })
                
#                 print(f"✅ تم تحميل البيانات المالية لـ {symbol} في {country}")
                
#             except Exception as e:
#                 print(f"❌ خطأ في تحميل البيانات المالية لـ {symbol}: {e}")
#                 results.append({
#                     "symbol": symbol,
#                     "country": country,
#                     "success": False,
#                     "error": str(e)
#                 })
        
#         success_count = sum(1 for r in results if r['success'])
        
#         return {
#             "message": f"✅ تم تحميل البيانات المالية لـ {success_count} من أصل {len(symbol_list)} رمز في {country}",
#             "country": country,
#             "period": period,
#             "results": results
#         }
        
#     except Exception as e:
#         print(f"❌ خطأ في تحميل البيانات المالية الجماعي: {e}")
#         raise HTTPException(status_code=500, detail=f"خطأ في تحميل البيانات المالية الجماعي: {str(e)}")