import httpx
from typing import Dict, Any, Optional
from app.core.config import BASE_URL, API_KEY

async def get_quote_data(symbol: str) -> Optional[Dict[str, Any]]:
    """جلب بيانات الـ quote للرمز المحدد"""
    try:
        print(f"🔄 جلب بيانات الـ quote للرمز: {symbol}")
        
        url = f"{BASE_URL}/quote"
        params = {
            "symbol": symbol,
            "apikey": API_KEY
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

        # التحقق من وجود خطأ في الاستجابة
        if "code" in data and data["code"] != 200:
            print(f"❌ خطأ في API للرمز {symbol}: {data.get('message', 'Unknown error')}")
            return None

        print(f"✅ تم جلب بيانات الـ quote للرمز: {symbol}")
        return data
        
    except Exception as e:
        print(f"❌ خطأ في get_quote_data للرمز {symbol}: {str(e)}")
        return None

def calculate_turnover(volume: str, close: str) -> float:
    """حساب الـ Turnover = volume × close"""
    try:
        volume_float = float(volume) if volume else 0
        close_float = float(close) if close else 0
        return volume_float * close_float
    except (ValueError, TypeError):
        return 0.0

async def get_enhanced_company_data(symbol: str) -> Dict[str, Any]:
    """جلب بيانات الشركة مع بيانات الـ quote المحسنة"""
    try:
        # جلب بيانات الـ quote
        quote_data = await get_quote_data(symbol)
        
        if not quote_data:
            return {}
        
        # استخراج البيانات المطلوبة
        enhanced_data = {
            "price": quote_data.get("close", "0"),
            "change": quote_data.get("change", "0"),
            "percent_change": quote_data.get("percent_change", "0"),
            "previous_close": quote_data.get("previous_close", "0"),
            "volume": quote_data.get("volume", "0"),
            "turnover": calculate_turnover(
                quote_data.get("volume", "0"), 
                quote_data.get("close", "0")
            ),
            "fifty_two_week": quote_data.get("fifty_two_week", {})
        }
        
        return enhanced_data
        
    except Exception as e:
        print(f"❌ خطأ في get_enhanced_company_data للرمز {symbol}: {str(e)}")
        return {}