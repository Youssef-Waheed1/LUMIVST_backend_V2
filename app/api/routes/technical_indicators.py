# app/api/routes/technical_indicators.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.core.config import settings
from app.services.database.technical_indicators_repository import TechnicalIndicatorsRepository
from app.services.twelve_data.technical_indicators import TechnicalIndicatorsService
from app.services.cache.technical_indicators_cache import technical_indicators_cache

router = APIRouter(prefix="/technical-indicators", tags=["technical-indicators"])
logger = logging.getLogger(__name__)

# Initialize services
indicators_service = TechnicalIndicatorsService(
    api_key=settings.API_KEY,
    base_url=settings.BASE_URL
)

@router.get("/test")
async def test_route():
    """Test route"""
    return {
        "message": "✅ Technical Indicators is working!",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(settings.API_KEY),
        "base_url": settings.BASE_URL
    }




@router.get("/")
async def get_all_indicators(db: Session = Depends(get_db), force_refresh: bool = Query(False)):
    """Get all available technical indicators from Twelve Data"""
    try:
        print(f"🔍 جلب قائمة المؤشرات الفنية من Twelve Data...")
        
        # إذا طلب المستخدم تحديث البيانات، نتجاهل الكاش
        if not force_refresh:
            # Try to get from cache first
            cached_indicators = await technical_indicators_cache.get_indicators_list()
            if cached_indicators:
                print(f"✅ تم جلب {len(cached_indicators.get('data', {}))} مؤشر من الكاش")
                return cached_indicators  # ✅ إرجاع البيانات كما هي من الكاش
        
        # Get from Twelve Data API (بيانات جديدة مطابقة للـ documentation)
        print(f"🌐 جلب المؤشرات من Twelve Data API...")
        api_response = await indicators_service.get_technical_indicators_list()
        
        print(f"📊 تم جلب {len(api_response.get('data', {}))} مؤشر من API")
        
        # Cache the results (بيانات جديدة مطابقة للـ documentation)
        if api_response.get('data'):
            await technical_indicators_cache.set_indicators_list(api_response)
            print(f"💾 تم تخزين المؤشرات في الكاش")
        
        return api_response  # ✅ إرجاع الـ response كما هو من الخدمة
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب المؤشرات الفنية: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في جلب المؤشرات الفنية: {str(e)}")

# @router.get("/")
# async def get_all_indicators(db: Session = Depends(get_db)):
#     """Get all available technical indicators from Twelve Data"""
#     try:
#         print(f"🔍 جلب قائمة المؤشرات الفنية من Twelve Data...")
        
#         # Try to get from cache first
#         cached_indicators = await technical_indicators_cache.get_indicators_list()
#         if cached_indicators:
#             print(f"✅ تم جلب {len(cached_indicators)} مؤشر من الكاش")
#             return {"indicators": cached_indicators, "source": "cache"}
        
#         # Get from Twelve Data API
#         print(f"🌐 جلب المؤشرات من Twelve Data API...")
#         api_response = await indicators_service.get_technical_indicators_list()
#         indicators = api_response.get("technical_indicators", [])
        
#         print(f"📊 تم جلب {len(indicators)} مؤشر من API")
        
#         # Cache the results
#         if indicators:
#             await technical_indicators_cache.set_indicators_list(indicators)
#             print(f"💾 تم تخزين المؤشرات في الكاش")
        
#         return {"indicators": indicators, "source": "twelve_data"}
        
#     except Exception as e:
#         logger.error(f"❌ خطأ في جلب المؤشرات الفنية: {e}")
#         raise HTTPException(status_code=500, detail=f"خطأ في جلب المؤشرات الفنية: {str(e)}")

@router.get("/categories/{category}")
async def get_indicators_by_category(
    category: str, 
    db: Session = Depends(get_db)
):
    """Get technical indicators by category"""
    try:
        print(f"🔍 جلب المؤشرات للتصنيف: {category}")
        
        # Get all indicators first
        all_indicators_response = await get_all_indicators(db)
        indicators_list = all_indicators_response.get("indicators", [])
        
        # Filter by category
        category_indicators = [
            indicator for indicator in indicators_list 
            if indicator.get("category", "").lower() == category.lower()
        ]
        
        print(f"📊 وجد {len(category_indicators)} مؤشر في تصنيف {category}")
        
        if not category_indicators:
            raise HTTPException(status_code=404, detail=f"لا توجد مؤشرات للتصنيف: {category}")
        
        return {
            "category": category, 
            "indicators": category_indicators, 
            "source": all_indicators_response.get("source", "unknown"),
            "count": len(category_indicators)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ خطأ في جلب المؤشرات للتصنيف {category}: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في جلب المؤشرات للتصنيف: {str(e)}")

@router.post("/{symbol}/calculate")
async def calculate_technical_indicator(
    symbol: str,
    indicator: str = Query(..., description="اسم المؤشر (مثل: macd, rsi, bollinger_bands)"),
    interval: str = Query("1day", description="الفترة الزمنية (1min, 5min, 1day, 1week)"),
    country: str = Query("Saudi Arabia", description="البلد"),
    outputsize: int = Query(100, description="عدد النقاط المطلوبة"),
    db: Session = Depends(get_db)
):
    try:
        print(f"📊 حساب المؤشر الفني: {symbol} -> {indicator} - البلد: {country} - الفترة: {interval}")
        
        # تنظيف الرمز وإضافة البورصة
        clean_symbol = symbol.upper().replace('.SA', '')
        exchange = get_exchange_by_country(country)
        
        # استخدام البلد والرمز معاً كمفتاح فريد (مثل الـ financials)
        cache_key = f"{country}:{clean_symbol}"
        
        # Check cache first
        cached_data = await technical_indicators_cache.get_indicator_data(
            cache_key, indicator, interval
        )
        if cached_data:
            print(f"✅ تم جلب بيانات {indicator} لـ {symbol} من الكاش")
            return {**cached_data, "source": "cache"}
        
        # Get from Twelve Data API
        print(f"🌐 جلب بيانات {indicator} من Twelve Data API لـ {clean_symbol}...")
        indicator_data = await indicators_service.get_indicator_data(
            symbol=clean_symbol,
            interval=interval,
            indicator=indicator,
            outputsize=outputsize,
            exchange=exchange
        )
        
        if not indicator_data or 'values' not in indicator_data:
            raise HTTPException(
                status_code=404, 
                detail=f"لا توجد بيانات للمؤشر {indicator} للرمز {symbol} في {country}"
            )
        
        # Save to database in background
        repo = TechnicalIndicatorsRepository(db)
        await save_indicator_data_to_db(repo, clean_symbol, country, indicator, interval, indicator_data)
        
        # Cache the result
        await technical_indicators_cache.set_indicator_data(
            cache_key, indicator, interval, indicator_data
        )
        
        records_count = len(indicator_data.get('values', []))
        print(f"✅ تم حساب المؤشر {indicator} لـ {symbol} - {records_count} نقطة بيانات")
        
        return {
            **indicator_data,
            "source": "twelve_data",
            "meta": {
                **indicator_data.get('meta', {}),
                "symbol": symbol,
                "clean_symbol": clean_symbol,
                "country": country,
                "exchange": exchange,
                "records_count": records_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ خطأ في حساب المؤشر {indicator} لـ {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في حساب المؤشر: {str(e)}")

@router.post("/load/{symbol}")
async def load_technical_indicators(
    symbol: str,
    indicators: List[str] = Query(..., description="قائمة المؤشرات المطلوبة (مفصولة بفواصل)"),
    interval: str = Query("1day", description="الفترة الزمنية"),
    country: str = Query("Saudi Arabia", description="البلد"),
    outputsize: int = Query(100, description="عدد النقاط المطلوبة"),
    db: Session = Depends(get_db)
):
    try:
        print(f"🔄 بدء تحميل المؤشرات الفنية لـ {symbol} - البلد: {country}")
        print(f"📋 المؤشرات المطلوبة: {indicators}")
        
        clean_symbol = symbol.upper().replace('.SA', '')
        exchange = get_exchange_by_country(country)
        cache_key = f"{country}:{clean_symbol}"
        
        results = {}
        
        for indicator in indicators:
            try:
                print(f"🔍 جلب المؤشر: {indicator}")
                
                # جلب البيانات من API
                indicator_data = await indicators_service.get_indicator_data(
                    symbol=clean_symbol,
                    interval=interval,
                    indicator=indicator,
                    outputsize=outputsize,
                    exchange=exchange
                )
                
                if indicator_data and 'values' in indicator_data:
                    # حفظ في قاعدة البيانات
                    repo = TechnicalIndicatorsRepository(db)
                    await save_indicator_data_to_db(repo, clean_symbol, country, indicator, interval, indicator_data)
                    
                    # تخزين في الكاش
                    await technical_indicators_cache.set_indicator_data(
                        cache_key, indicator, interval, indicator_data
                    )
                    
                    records_count = len(indicator_data.get('values', []))
                    results[indicator] = {
                        "success": True,
                        "records": records_count,
                        "source": "twelve_data"
                    }
                    
                    print(f"✅ تم تحميل المؤشر {indicator} لـ {symbol} - {records_count} سجل")
                else:
                    results[indicator] = {
                        "success": False,
                        "error": "لا توجد بيانات"
                    }
                    print(f"⚠️ لا توجد بيانات للمؤشر {indicator}")
                
            except Exception as e:
                logger.error(f"❌ خطأ في تحميل المؤشر {indicator} لـ {symbol}: {e}")
                results[indicator] = {
                    "success": False,
                    "error": str(e)
                }
        
        success_count = sum(1 for r in results.values() if r.get('success'))
        
        return {
            "message": f"✅ تم تحميل {success_count} من أصل {len(indicators)} مؤشر لـ {symbol}",
            "symbol": symbol,
            "clean_symbol": clean_symbol,
            "country": country,
            "exchange": exchange,
            "interval": interval,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل المؤشرات الفنية لـ {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في تحميل المؤشرات الفنية: {str(e)}")

@router.get("/{symbol}/data")
async def get_technical_indicator_data_from_db(
    symbol: str,
    indicator: str = Query(..., description="اسم المؤشر"),
    timeframe: str = Query("1day", description="الإطار الزمني"),
    country: str = Query("Saudi Arabia", description="البلد"),
    start_date: Optional[datetime] = Query(None, description="تاريخ البداية"),
    end_date: Optional[datetime] = Query(None, description="تاريخ النهاية"),
    limit: int = Query(100, description="عدد النقاط المطلوبة"),
    db: Session = Depends(get_db)
):
    try:
        print(f"📊 جلب بيانات المؤشر من قاعدة البيانات لـ {symbol} - {indicator} - {timeframe}")
        
        # تعيين التواريخ إذا لم يتم توفيرها
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=365)  # سنة كاملة
        
        repo = TechnicalIndicatorsRepository(db)
        indicator_data = repo.get_indicator_data(
            symbol=symbol,
            indicator_name=indicator,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        # تطبيق الحد الأقصى
        if limit and len(indicator_data) > limit:
            indicator_data = indicator_data[:limit]
        
        print(f"📈 وجد {len(indicator_data)} سجل في قاعدة البيانات")
        
        # تحويل البيانات إلى JSON
        def serialize_item(item):
            result = {
                "symbol": item.symbol,
                "indicator_name": item.indicator_name,
                "timeframe": item.timeframe,
                "date": item.date.isoformat() if hasattr(item.date, 'isoformat') else str(item.date),
                "values": item.values
            }
            if hasattr(item, 'id'):
                result["id"] = str(item.id)
            if hasattr(item, 'created_at'):
                result["created_at"] = item.created_at.isoformat() if hasattr(item.created_at, 'isoformat') else str(item.created_at)
            return result
        
        response_data = {
            "indicator_data": [serialize_item(item) for item in indicator_data],
            "meta": {
                "symbol": symbol,
                "indicator": indicator,
                "timeframe": timeframe,
                "country": country,
                "records_count": len(indicator_data),
                "date_range": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            }
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب بيانات المؤشر من DB لـ {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في جلب بيانات المؤشر: {str(e)}")

@router.get("/status")
async def get_service_status():
    """حالة الخدمة والتبعيات"""
    return {
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "api_key_configured": bool(settings.API_KEY),
        "base_url": settings.BASE_URL,
        "cache_service": True,
        "database": True
    }

# Helper functions
def get_exchange_by_country(country: str) -> str:
    """الحصول على رمز البورصة بناءً على البلد"""
    exchanges = {
        "Saudi Arabia": "TADAWUL",
        "UAE": "DFM",
        "Egypt": "EGX", 
        "Qatar": "QE",
        "Kuwait": "BKP",
        "Oman": "MSM",
        "Bahrain": "BSE"
    }
    return exchanges.get(country, "TADAWUL")

async def save_indicator_data_to_db(repo: TechnicalIndicatorsRepository, symbol: str, country: str, 
                                  indicator: str, interval: str, indicator_data: Dict[str, Any]):
    """حفظ بيانات المؤشر في قاعدة البيانات"""
    try:
        if 'values' in indicator_data:
            saved_count = 0
            for data_point in indicator_data['values']:
                if 'datetime' in data_point:
                    # تحويل التاريخ
                    date_str = data_point['datetime']
                    try:
                        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        try:
                            date = datetime.strptime(date_str, '%Y-%m-%d')
                        except:
                            date = datetime.now()
                    
                    # استخراج القيم (استبعاد datetime)
                    values = {k: v for k, v in data_point.items() if k != 'datetime' and v is not None}
                    
                    if values:  # فقط إذا كانت هناك قيم
                        # حفظ في قاعدة البيانات
                        from app.schemas.technical_indicators import TechnicalIndicatorDataCreate
                        db_data = TechnicalIndicatorDataCreate(
                            symbol=symbol,
                            indicator_name=indicator,
                            timeframe=interval,
                            date=date,
                            values=values
                        )
                        repo.save_indicator_data(db_data)
                        saved_count += 1
            
            print(f"💾 تم حفظ {saved_count} سجل في قاعدة البيانات للمؤشر {indicator}")
                    
    except Exception as e:
        logger.error(f"⚠️ خطأ في حفظ بيانات المؤشر في DB: {e}")
        # لا نرفع خطأ هنا علشان ما نعطلش الـ response الرئيسي

# إضافة دالة لتنظيف الكاش وإعادة التحميل
@router.delete("/cache/clear")
async def clear_indicators_cache():
    """تنظيف كاش المؤشرات الفنية وإعادة التحميل"""
    try:
        # تنظيف الكاش
        await technical_indicators_cache.redis.delete(
            technical_indicators_cache.get_indicators_list_key()
        )
        
        print("✅ تم تنظيف كاش المؤشرات الفنية")
        return {"message": "تم تنظيف الكاش بنجاح", "status": "success"}
    except Exception as e:
        logger.error(f"❌ خطأ في تنظيف الكاش: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في تنظيف الكاش: {str(e)}")
    

