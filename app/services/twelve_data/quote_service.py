
import httpx
from typing import Dict, List, Any, Optional
from app.core.config import settings
from datetime import datetime
from app.utils.saudi_time import utc_timestamp_to_saudi, get_saudi_metadata

def clean_symbol(symbol: str) -> str:
    """تنظيف رمز الشركة"""
    if not symbol:
        return ""
    return ''.join(filter(str.isdigit, symbol)).upper()

async def get_stock_quote(symbol: str, country: str = "Saudi Arabia") -> Optional[Dict[str, Any]]:
    """جلب بيانات السعر والتغيرات للسهم مع تحويل التوقيت للسعودية"""
    try:
        clean_sym = clean_symbol(symbol)
        
        url = "https://api.twelvedata.com/quote"
        params = {
            "symbol": clean_sym,
            "country": country,
            "apikey": API_KEY
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            data = response.json()

        # التحقق من وجود بيانات صالحة
        if "code" in data or data.get("close") is None:
            return None
        
        return await _process_quote_data(data, clean_sym)
        
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات السعر للسهم {symbol}: {str(e)}")
        return None

async def _process_quote_data(raw_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """معالجة البيانات الخام مع تحويل التوقيت للسعودية"""
    
    fifty_two_week = raw_data.get("fifty_two_week", {})
    
    # تحويل timestamp من الـ API للتوقيت السعودي
    api_timestamp = raw_data.get("timestamp")
    saudi_time = utc_timestamp_to_saudi(api_timestamp) if api_timestamp else {"datetime": None, "timestamp": None}
    
    # الحصول على metadata السعودي
    metadata = get_saudi_metadata()
    
    return {
        "symbol": symbol,
        "name": raw_data.get("name"),
        "exchange": metadata["exchange"],
        "mic_code": metadata["mic_code"],
        "currency": metadata["currency"],
        
        # ⭐ التوقيت السعودي بدلاً من UTC
        "datetime": saudi_time["datetime"],
        "timestamp": saudi_time["timestamp"],
        "timezone": metadata["timezone"],
        
        "open": _safe_str(raw_data.get("open")),
        "high": _safe_str(raw_data.get("high")),
        "low": _safe_str(raw_data.get("low")),
        "close": _safe_str(raw_data.get("close")),
        "volume": _safe_str(raw_data.get("volume")),
        "previous_close": _safe_str(raw_data.get("previous_close")),
        "change": _safe_str(raw_data.get("change")),
        "percent_change": _safe_str(raw_data.get("percent_change")),
        "average_volume": _safe_str(raw_data.get("average_volume")),
        "is_market_open": raw_data.get("is_market_open", False),
        
        # بيانات 52 أسبوع
        "fifty_two_week": fifty_two_week,
        "fifty_two_week_low": _safe_str(fifty_two_week.get("low")),
        "fifty_two_week_high": _safe_str(fifty_two_week.get("high")),
        "fifty_two_week_low_change": _safe_str(fifty_two_week.get("low_change")),
        "fifty_two_week_high_change": _safe_str(fifty_two_week.get("high_change")),
        "fifty_two_week_low_change_percent": _safe_str(fifty_two_week.get("low_change_percent")),
        "fifty_two_week_high_change_percent": _safe_str(fifty_two_week.get("high_change_percent")),
        "fifty_two_week_range": fifty_two_week.get("range"),
        
        "last_updated": metadata["datetime"]
    }

def _safe_str(value: any) -> Optional[str]:
    """تحويل آمن للقيمة إلى string"""
    if value is None or value == "":
        return None
    return str(value)

async def get_multiple_quotes(symbols: List[str], country: str = "Saudi Arabia") -> List[Dict[str, Any]]:
    """جلب بيانات السعر لعدة رموز"""
    import asyncio
    
    tasks = [get_stock_quote(symbol, country) for symbol in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    quotes = []
    for result in results:
        if isinstance(result, Exception) or result is None:
            continue
        quotes.append(result)
    
    return quotes

def _calculate_turnover(volume: str, close_price: str) -> str:
    """حساب قيمة التداول"""
    try:
        if volume and close_price and volume != "N/A" and close_price != "N/A":
            volume_num = float(str(volume).replace(',', ''))
            close_num = float(str(close_price).replace(',', ''))
            turnover = volume_num * close_num
            return f"{turnover:,.0f}"
        return "N/A"
    except (ValueError, TypeError):
        return "N/A"