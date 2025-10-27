import httpx
import math
from typing import Dict, List, Any
from app.core.config import BASE_URL, API_KEY

def clean_company_symbol(symbol: str) -> str:
    """
    تنظيف رمز الشركة مع الحفاظ على الرموز الحقيقية
    """
    if not symbol:
        return ""
    
    # إذا كان الرمز يحتوي على نقطة (مثل 1050.SARE) نأخذ الجزء قبل النقطة فقط
    if '.' in symbol:
        clean_symbol = symbol.split('.')[0].upper().strip()
    else:
        # إذا كان الرمز لا يحتوي على نقطة، نستخدمه كما هو
        clean_symbol = symbol.upper().strip()
    
    # إزالة الأقواس والمسافات الزائدة
    clean_symbol = clean_symbol.replace('(', '').replace(')', '').strip()
    
    return clean_symbol

def is_valid_company(company: dict) -> bool:
    """
    التحقق إذا كانت الشركة حقيقية وليست مكررة مزيفة
    """
    symbol = company.get('symbol', '')
    name = company.get('name', '')
    
    # إذا كان اسم الشركة هو نفس الرمز (مثل "1050.SARE") فهي مزيفة
    if symbol and name and symbol.upper() == name.upper():
        return False
    
    # إذا كان الاسم فارغاً أو لا معنى له
    if not name or name.strip() == '':
        return False
    
    # شرط إضافي: التحقق من أن الاسم ليس مجرد أرقام
    if name.replace('.', '').replace(' ', '').isdigit():
        return False
    
    # إذا كان الاسم قصير جداً (أقل من 3 أحرف)
    if len(name.strip()) < 3:
        return False
    
    return True

async def get_companies(page: int = 1, limit: int = 100, remove_duplicates: bool = True) -> Dict[str, Any]:
    """Fetch list of companies from the Saudi Stock Exchange (TADAWUL) with pagination and filtering."""
    try:
        print(f"🔄 جلب بيانات الشركات من API... الصفحة {page}, العدد {limit}, تصفية: {remove_duplicates}")
        url = f"{BASE_URL}/stocks"
        params = {
            "exchange": "TADAWUL",
            "apikey": API_KEY
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

        if "data" not in data:
            raise ValueError(f"Error fetching companies: {data}")

        all_companies = data["data"]
        print(f"✅ تم جلب {len(all_companies)} شركة من API")
        
        # تطبيق التصفية إذا مطلوب
        if remove_duplicates:
            cleaned_data = []
            seen_symbols = set()
            removed_count = 0
            
            for company in all_companies:
                # تخطي الشركات المزيفة
                if not is_valid_company(company):
                    removed_count += 1
                    continue
                
                # تنظيف الرمز
                original_symbol = company['symbol']
                clean_symbol = clean_company_symbol(original_symbol)
                
                # إذا كان الرمز غير مكرر، أضفه
                if clean_symbol and clean_symbol not in seen_symbols:
                    seen_symbols.add(clean_symbol)
                    # تحديث الرمز إلى الصيغة النظيفة
                    company['symbol'] = clean_symbol
                    company['original_symbol'] = original_symbol
                    cleaned_data.append(company)
                else:
                    removed_count += 1
            
            all_companies = cleaned_data
            print(f"🎯 بعد التصفية: {len(all_companies)} شركة (تم حذف {removed_count} شركة)")
        
        # تطبيق الـ pagination على البيانات (سواء كانت مصفاة أو لا)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        
        # تأكد من أن المؤشرات within range
        total_companies = len(all_companies)
        if start_index >= total_companies:
            paginated_companies = []
            # إذا طلب صفحة غير موجودة، ارجع الصفحة الأولى
            if page > 1:
                start_index = 0
                end_index = limit
                paginated_companies = all_companies[start_index:end_index]
                page = 1
        else:
            paginated_companies = all_companies[start_index:end_index]
        
        # حساب metadata للـ pagination
        total_pages = math.ceil(total_companies / limit) if total_companies > 0 else 1
        
        print(f"📄 Pagination: الصفحة {page}/{total_pages} - {len(paginated_companies)} شركة من أصل {total_companies}")
        
        return {
            "data": paginated_companies,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_companies,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "prev_page": page - 1 if page > 1 else None
            }
        }
        
    except Exception as e:
        print(f"❌ خطأ في get_companies: {str(e)}")
        raise ValueError(f"Error in get_companies: {str(e)}")