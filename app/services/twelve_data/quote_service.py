import httpx
from typing import Dict, List, Any, Optional
from app.core.config import API_KEY
from app.schemas.quote import StockQuoteCreate, FiftyTwoWeek
from datetime import datetime

def clean_symbol(symbol: str) -> str:
    """تنظيف رمز الشركة"""
    if not symbol:
        return ""
    return ''.join(filter(str.isdigit, symbol)).upper()

async def get_stock_quote(symbol: str, country: str = "Saudi Arabia") -> Optional[Dict[str, Any]]:
    """جلب بيانات السعر والتغيرات للسهم"""
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
        
        # ⭐⭐ معالجة البيانات لتتوافق مع الـ Schema
        processed_data = await _process_quote_data(data, clean_sym)
        return processed_data
        
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات السعر للسهم {symbol}: {str(e)}")
        return None

async def _process_quote_data(raw_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """معالجة البيانات الخام لتتوافق مع الـ Schema"""
    
    # استخراج بيانات 52 أسبوع
    fifty_two_week = {
        "low": raw_data.get("fifty_two_week", {}).get("low"),
        "high": raw_data.get("fifty_two_week", {}).get("high"),
        "low_change": raw_data.get("fifty_two_week", {}).get("low_change"),
        "high_change": raw_data.get("fifty_two_week", {}).get("high_change"),
        "low_change_percent": raw_data.get("fifty_two_week", {}).get("low_change_percent"),
        "high_change_percent": raw_data.get("fifty_two_week", {}).get("high_change_percent"),
        "range": raw_data.get("fifty_two_week", {}).get("range")
    }
    
    # بناء البيانات المعالجة
    processed_data = {
        "symbol": symbol,
        "name": raw_data.get("name"),
        "exchange": raw_data.get("exchange", "Tadawul"),
        "mic_code": raw_data.get("mic_code"),
        "currency": raw_data.get("currency", "SAR"),
        "datetime": raw_data.get("datetime"),
        "timestamp": raw_data.get("timestamp"),
        "last_quote_at": raw_data.get("last_quote_at"),
        "open": str(raw_data.get("open")) if raw_data.get("open") else None,
        "high": str(raw_data.get("high")) if raw_data.get("high") else None,
        "low": str(raw_data.get("low")) if raw_data.get("low") else None,
        "close": str(raw_data.get("close")) if raw_data.get("close") else None,
        "volume": str(raw_data.get("volume")) if raw_data.get("volume") else None,
        "previous_close": str(raw_data.get("previous_close")) if raw_data.get("previous_close") else None,
        "change": str(raw_data.get("change")) if raw_data.get("change") else None,
        "percent_change": str(raw_data.get("percent_change")) if raw_data.get("percent_change") else None,
        "average_volume": str(raw_data.get("average_volume")) if raw_data.get("average_volume") else None,
        "is_market_open": raw_data.get("is_market_open", False),
        
        # ⭐⭐ بيانات 52 أسبوع المعالجة
        "fifty_two_week": fifty_two_week,
        "fifty_two_week_low": str(fifty_two_week.get("low")) if fifty_two_week.get("low") else None,
        "fifty_two_week_high": str(fifty_two_week.get("high")) if fifty_two_week.get("high") else None,
        "fifty_two_week_low_change": str(fifty_two_week.get("low_change")) if fifty_two_week.get("low_change") else None,
        "fifty_two_week_high_change": str(fifty_two_week.get("high_change")) if fifty_two_week.get("high_change") else None,
        "fifty_two_week_low_change_percent": str(fifty_two_week.get("low_change_percent")) if fifty_two_week.get("low_change_percent") else None,
        "fifty_two_week_high_change_percent": str(fifty_two_week.get("high_change_percent")) if fifty_two_week.get("high_change_percent") else None,
        "fifty_two_week_range": fifty_two_week.get("range"),
        
        # ⭐⭐ الحقول الإضافية المطلوبة في Schema
        "extended_price": None,
        "extended_change": None,
        "extended_percent_change": None,
        "extended_timestamp": None,
        
        "last_updated": datetime.now().isoformat()
    }
    
    # طباعة بيانات التصحيح
    print(f"✅ البيانات المعالجة للرمز {symbol}:")
    print(f"   - 52-week range: {processed_data.get('fifty_two_week_range')}")
    print(f"   - 52-week low: {processed_data.get('fifty_two_week_low')}")
    print(f"   - 52-week high: {processed_data.get('fifty_two_week_high')}")
    print(f"   - Full 52-week object: {processed_data.get('fifty_two_week')}")
    
    return processed_data

async def get_multiple_quotes(symbols: List[str], country: str = "Saudi Arabia") -> List[Dict[str, Any]]:  # ⭐ تم التعديل
    """جلب بيانات السعر لعدة رموز"""
    import asyncio
    
    tasks = [get_stock_quote(symbol, country) for symbol in symbols]  # ⭐ تم التعديل
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    quotes = []
    for result in results:
        if isinstance(result, Exception) or result is None:
            continue
        quotes.append(result)
    
    return quotes

def convert_quote_to_schema(quote_data: Dict[str, Any]) -> StockQuoteCreate:
    """تحويل بيانات API إلى schema"""
    fifty_two_week = quote_data.get("fifty_two_week", {})
    
    return StockQuoteCreate(
        symbol=quote_data.get("symbol", ""),
        currency=quote_data.get("currency", "SAR"),
        datetime=quote_data.get("datetime"),
        timestamp=quote_data.get("timestamp"),
        open=float(quote_data.get("open", 0)) if quote_data.get("open") and quote_data.get("open") != "N/A" else None,
        high=float(quote_data.get("high", 0)) if quote_data.get("high") and quote_data.get("high") != "N/A" else None,
        low=float(quote_data.get("low", 0)) if quote_data.get("low") and quote_data.get("low") != "N/A" else None,
        close=float(quote_data.get("close", 0)) if quote_data.get("close") and quote_data.get("close") != "N/A" else None,
        volume=int(quote_data.get("volume", 0)) if quote_data.get("volume") and quote_data.get("volume") != "N/A" else None,
        previous_close=float(quote_data.get("previous_close", 0)) if quote_data.get("previous_close") and quote_data.get("previous_close") != "N/A" else None,
        change=float(quote_data.get("change", 0)) if quote_data.get("change") and quote_data.get("change") != "N/A" else None,
        percent_change=float(quote_data.get("percent_change", 0)) if quote_data.get("percent_change") and quote_data.get("percent_change") != "N/A" else None,
        average_volume=int(quote_data.get("average_volume", 0)) if quote_data.get("average_volume") and quote_data.get("average_volume") != "N/A" else None,
        is_market_open=quote_data.get("is_market_open", False),
        fifty_two_week=FiftyTwoWeek(
            low=float(fifty_two_week.get("low", 0)) if fifty_two_week.get("low") and fifty_two_week.get("low") != "N/A" else None,
            high=float(fifty_two_week.get("high", 0)) if fifty_two_week.get("high") and fifty_two_week.get("high") != "N/A" else None,
            low_change=float(fifty_two_week.get("low_change", 0)) if fifty_two_week.get("low_change") and fifty_two_week.get("low_change") != "N/A" else None,
            high_change=float(fifty_two_week.get("high_change", 0)) if fifty_two_week.get("high_change") and fifty_two_week.get("high_change") != "N/A" else None,
            low_change_percent=float(fifty_two_week.get("low_change_percent", 0)) if fifty_two_week.get("low_change_percent") and fifty_two_week.get("low_change_percent") != "N/A" else None,
            high_change_percent=float(fifty_two_week.get("high_change_percent", 0)) if fifty_two_week.get("high_change_percent") and fifty_two_week.get("high_change_percent") != "N/A" else None,
            range=fifty_two_week.get("range")
        )
    )

def _calculate_turnover(volume: str, close_price: str) -> str:
    """حساب قيمة التداول (Turnover)"""
    try:
        if volume and close_price and volume != "N/A" and close_price != "N/A":
            volume_num = float(str(volume).replace(',', ''))
            close_num = float(str(close_price).replace(',', ''))
            turnover = volume_num * close_num
            return f"{turnover:,.0f}"
        return "N/A"
    except (ValueError, TypeError):
        return "N/A"