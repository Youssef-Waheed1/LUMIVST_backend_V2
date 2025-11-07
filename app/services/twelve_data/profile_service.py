import httpx
from typing import Dict, List, Any, Optional
from app.core.config import API_KEY
from app.schemas.profile import CompanyProfileCreate, CompanyProfileResponse

def clean_symbol(symbol: str) -> str:
    """تنظيف رمز الشركة"""
    if not symbol:
        return ""
    return ''.join(filter(str.isdigit, symbol)).upper()

async def get_company_profile(symbol: str, country: str = "Saudi Arabia") -> Optional[Dict[str, Any]]:  # ⭐ تم التعديل
    """جلب بيانات الملف الشخصي للشركة"""
    try:
        clean_sym = clean_symbol(symbol)
        
        url = "https://api.twelvedata.com/profile"
        params = {
            "symbol": clean_sym,
            "country": country,  # ⭐ جديد
            "apikey": API_KEY
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

async def get_multiple_profiles(symbols: List[str], country: str = "Saudi Arabia") -> List[Dict[str, Any]]:  # ⭐ تم التعديل
    """جلب بيانات الملف الشخصي لعدة رموز"""
    import asyncio
    
    tasks = [get_company_profile(symbol, country) for symbol in symbols]  # ⭐ تم التعديل
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    profiles = []
    for result in results:
        if isinstance(result, Exception) or result is None:
            continue
        profiles.append(result)
    
    return profiles

def convert_profile_to_schema(profile_data: Dict[str, Any]) -> CompanyProfileCreate:
    """تحويل بيانات API إلى schema"""
    return CompanyProfileCreate(
        symbol=profile_data.get("symbol", ""),
        name=profile_data.get("name", "N/A"),
        exchange=profile_data.get("exchange", "Tadawul"),
        sector=profile_data.get("sector"),
        industry=profile_data.get("industry"),
        employees=profile_data.get("employees"),
        website=profile_data.get("website"),
        description=profile_data.get("description"),
        state=profile_data.get("state"),
        country=profile_data.get("country"),
        logo_url=profile_data.get("logo_url"),
        phone=profile_data.get("phone"),
        address=profile_data.get("address"),
        city=profile_data.get("city"),
        zip_code=profile_data.get("zip_code")
    )