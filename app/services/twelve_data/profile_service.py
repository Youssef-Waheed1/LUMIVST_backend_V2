# app/services/twelve_data/profile_service.py

import httpx
from typing import Dict, List, Any, Optional
from app.core.config import settings

def clean_symbol(symbol: str) -> str:
    """تنظيف رمز الشركة"""
    if not symbol:
        return ""
    return ''.join(filter(str.isdigit, symbol)).upper()

async def get_company_profile(symbol: str, country: str = "Saudi Arabia") -> Optional[Dict[str, Any]]:
    """جلب بيانات الملف الشخصي للشركة"""
    try:
        clean_sym = clean_symbol(symbol)
        
        url = "https://api.twelvedata.com/profile"
        params = {
            "symbol": clean_sym,
            "country": country,
            "apikey": settings.API_KEY
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            data = response.json()

        # التحقق من وجود بيانات صالحة
        if "code" in data or data.get("symbol") is None:
            return None
            
        return data
        
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات الملف الشخصي للسهم {symbol}: {str(e)}")
        return None

async def get_multiple_profiles(symbols: List[str], country: str = "Saudi Arabia") -> List[Dict[str, Any]]:
    """جلب بيانات الملف الشخصي لعدة رموز"""
    import asyncio
    
    tasks = [get_company_profile(symbol, country) for symbol in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    profiles = []
    for result in results:
        if isinstance(result, Exception) or result is None:
            continue
        profiles.append(result)
    
    return profiles

# ⭐⭐⭐ حذف الدالة convert_profile_to_schema لأنها مش مستخدمة