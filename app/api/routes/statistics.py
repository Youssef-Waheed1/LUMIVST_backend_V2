from fastapi import APIRouter, HTTPException, Query
import httpx
import os
from typing import Dict, Any

router = APIRouter()

#  قائمة الرموز السعودية المعتمدة
SAUDI_STOCKS = {
    "1010", "1020", "1030", "1050", "1060", "1080", "1111", "1120", "1140", 
    "1150", "1180", "1182", "1183", "1201", "1202", "1210", "1211", "1212",
    "1213", "1214", "1301", "1302", "1303", "1304", "1320", "1321", "1322",
    "1323", "1810", "1820", "1830", "1831", "1832", "1833", "2001", "2010", 
    "2020", "2030", "2040", "2050", "2060", "2070", "2080", "2081", "2082",
    "2083", "2090", "2100", "2110", "2120", "2130", "2140", "2150", "2160", 
    "2170", "2180", "2190", "2200", "2210", "2220", "2222", "2223", "2230", 
    "2240", "2250", "2270", "2280", "2281", "2282", "2283", "2284", "2285", 
    "2286", "2287", "2290", "2300", "2310", "2320", "2330", "2340", "2350", 
    "2360", "2370", "2380", "2381", "2382", "3001", "3002", "3003", "3004", 
    "3005", "3007", "3008", "3010", "3020", "3030", "3040", "3050", "3060",
    "3080", "3090", "3091", "3092", "4001", "4002", "4003", "4004", "4005"
}

def clean_symbol(symbol: str) -> str:
    """تنظيف الرمز للإنتاج"""
    if not symbol:
        return ""
    return ''.join(filter(str.isdigit, symbol)).upper()

@router.get("/statistics/{symbol}")
async def get_statistics_test(
    symbol: str,
    country: str = Query("Saudi Arabia", description="البلد")
):
    """
    endpoint تجريبي مبسط للإحصائيات
    """
    try:
        print(f"🔍 اختبار الإحصائيات لـ: {symbol} في {country}")
        
        # تنظيف الرمز والتحقق من وجوده في القائمة
        clean_symbol_val = clean_symbol(symbol)
        
        if clean_symbol_val not in SAUDI_STOCKS:
            return {
                "error": "رمز غير مدعوم",
                "message": f"الرمز {symbol} غير موجود في قائمة الأسهم السعودية المدعومة",
                "supported_symbols": list(SAUDI_STOCKS)[:10],  # عرض أول 10 رموز فقط
                "total_supported": len(SAUDI_STOCKS)
            }
        
        # جلب البيانات مباشرة من API
        api_key = os.getenv("TWELVE_DATA_API_KEY", "demo")
        url = "https://api.twelvedata.com/statistics"
        
        params = {
            "symbol": clean_symbol_val,
            "country": country,
            "apikey": api_key
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30)
            data = response.json()
            
            print(f"✅ استجابة API لـ {clean_symbol_val}: {response.status_code}")
            
            if 'error' in data:
                return {
                    "error": data['error'],
                    "message": f"لا توجد بيانات إحصائيات لـ {symbol} في {country}",
                    "symbol": symbol,
                    "clean_symbol": clean_symbol_val,
                    "country": country
                }
            
            return {
                "symbol": symbol,
                "clean_symbol": clean_symbol_val,
                "country": country,
                "data": data,
                "is_supported": True
            }
            
    except Exception as e:
        print(f"❌ خطأ: {e}")
        raise HTTPException(status_code=500, detail=f"خطأ في جلب البيانات: {str(e)}")

@router.get("/statistics/supported/symbols")
async def get_supported_symbols():
    """الحصول على قائمة الرموز المدعومة"""
    return {
        "supported_symbols": list(SAUDI_STOCKS),
        "total_symbols": len(SAUDI_STOCKS),
        "last_updated": "2024-01-01"
    }

@router.get("/statistics/test/hello")
async def test_hello():
    """اختبار بسيط للتأكد من عمل الـ router"""
    return {
        "message": "✅ statistics router working!",
        "status": "success",
        "supported_symbols_count": len(SAUDI_STOCKS)
    }