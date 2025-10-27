from fastapi import APIRouter, HTTPException, Query
from app.services.cache.company_cache import company_cache
import traceback

router = APIRouter(prefix="/stocks", tags=["Companies"])

@router.get("")
async def get_companies_paginated(
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(50, ge=1, le=500, description="Number of items per page (max: 500)"),
    remove_duplicates: bool = Query(True, description="Remove duplicate companies")
):
    """
    Get paginated list of companies from Saudi Stock Exchange (TADAWUL)
    مع تطبيق الكاش التلقائي
    """
    try:
        print(f"📨 طلب pagination مع الكاش: الصفحة {page}, الـ limit {limit}")
        
        # جلب البيانات من الكاش (الذي سيتحقق من API إذا لزم الأمر)
        result = await company_cache.get_companies(
            page=page, 
            limit=limit, 
            remove_duplicates=remove_duplicates
        )
        
        print(f"✅ تم إرجاع {len(result['data'])} شركة للصفحة {page} من أصل {result['pagination']['total']} شركة")
        
        return result
        
    except ValueError as e:
        print(f"❌ خطأ في get_companies_paginated: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"❌ خطأ غير متوقع في get_companies_paginated: {e}")
        print(f"🔍 تفاصيل الخطأ: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/{symbol}")
async def get_company_by_symbol(symbol: str):
    """
    Get company by symbol (supports both clean and full symbols)
    مع تطبيق الكاش التلقائي
    """
    try:
        print(f"🔍 البحث عن الشركة بالرمز مع الكاش: {symbol}")
        
        # البحث في الكاش (الذي سيتحقق من API إذا لزم الأمر)
        company = await company_cache.get_company_by_symbol(symbol)
        
        if not company:
            print(f"❌ الشركة غير موجودة: {symbol}")
            raise HTTPException(
                status_code=404, 
                detail=f"Company with symbol '{symbol}' not found"
            )
        
        print(f"✅ تم العثور على الشركة: {company['name']}")
        return company
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ خطأ غير متوقع في get_company_by_symbol: {e}")
        print(f"🔍 تفاصيل الخطأ: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")