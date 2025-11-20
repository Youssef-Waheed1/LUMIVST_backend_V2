# app/services/twelve_data/quote_service.py

import httpx
from typing import Dict, List, Any, Optional
from app.core.config import API_KEY
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
        
        return await _process_quote_data(data, clean_sym)
        
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات السعر للسهم {symbol}: {str(e)}")
        return None

async def _process_quote_data(raw_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """معالجة البيانات الخام"""
    
    fifty_two_week = raw_data.get("fifty_two_week", {})
    
    return {
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
        
        "fifty_two_week": fifty_two_week,
        "fifty_two_week_low": str(fifty_two_week.get("low")) if fifty_two_week.get("low") else None,
        "fifty_two_week_high": str(fifty_two_week.get("high")) if fifty_two_week.get("high") else None,
        "fifty_two_week_low_change": str(fifty_two_week.get("low_change")) if fifty_two_week.get("low_change") else None,
        "fifty_two_week_high_change": str(fifty_two_week.get("high_change")) if fifty_two_week.get("high_change") else None,
        "fifty_two_week_low_change_percent": str(fifty_two_week.get("low_change_percent")) if fifty_two_week.get("low_change_percent") else None,
        "fifty_two_week_high_change_percent": str(fifty_two_week.get("high_change_percent")) if fifty_two_week.get("high_change_percent") else None,
        "fifty_two_week_range": fifty_two_week.get("range"),
        
        "last_updated": datetime.now().isoformat()
    }

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

# ⭐⭐⭐ حذف الدالة convert_quote_to_schema لأنها مش مستخدمة

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