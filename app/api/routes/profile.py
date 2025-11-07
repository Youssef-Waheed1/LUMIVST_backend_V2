from fastapi import APIRouter, HTTPException, Query
from app.services.twelve_data.profile_service import get_company_profile, get_multiple_profiles
from app.schemas.profile import CompanyProfileResponse

router = APIRouter(prefix="/profile", tags=["Company Profiles"])

@router.get("/{symbol}", response_model=CompanyProfileResponse)
async def get_company_profile_endpoint(
    symbol: str,
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")  # ⭐ جديد
):
    """جلب الملف الشخصي لشركة معينة"""
    try:
        profile_data = await get_company_profile(symbol, country)  # ⭐ تم التعديل
        
        if not profile_data:
            raise HTTPException(status_code=404, detail=f"Company profile for '{symbol}' not found")
        
        return profile_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ خطأ في جلب الملف الشخصي: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=list[CompanyProfileResponse])
async def get_multiple_profiles_endpoint(
    symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل"),
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")  # ⭐ جديد
):
    """جلب الملفات الشخصية لعدة شركات"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        if len(symbol_list) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 symbols allowed")
        
        profiles = await get_multiple_profiles(symbol_list, country)  # ⭐ تم التعديل
        
        return profiles
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ خطأ في جلب الملفات الشخصية: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")