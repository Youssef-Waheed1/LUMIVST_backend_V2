import json
from typing import Dict, List, Optional, Any
from app.core.redis import redis_cache

def clean_company_symbol(symbol: str) -> str:
    """
    نسخة مستقلة من دالة تنظيف الرمز لتجنب الاستيراد الدائري
    """
    if not symbol:
        return ""
    
    if '.' in symbol:
        clean_symbol = symbol.split('.')[0].upper().strip()
    else:
        clean_symbol = symbol.upper().strip()
    
    clean_symbol = clean_symbol.replace('(', '').replace(')', '').strip()
    return clean_symbol

class CompanyCache:
    def __init__(self):
        self.cache_prefix = "companies"
        self.cache_expire = 86400  # 24 ساعة
    
    def _get_cache_key(self, page: int, limit: int, remove_duplicates: bool) -> str:
        """إنشاء مفتاح كاش فريد بناءً على المعلمات"""
        return f"{self.cache_prefix}:page:{page}:limit:{limit}:filter:{remove_duplicates}"
    
    def _get_symbol_cache_key(self, symbol: str) -> str:
        """إنشاء مفتاح كاش للرمز"""
        clean_symbol = clean_company_symbol(symbol)
        return f"{self.cache_prefix}:symbol:{clean_symbol}"
    
    async def _fetch_companies_from_api(self, page: int = 1, limit: int = 100, remove_duplicates: bool = True) -> Dict[str, Any]:
        """استيراد دالة API بشكل ديناميكي لتجنب الاستيراد الدائري"""
        from app.services.twelve_data.companies import get_companies
        return await get_companies(page=page, limit=limit, remove_duplicates=remove_duplicates)
    
    async def get_companies(self, page: int = 1, limit: int = 100, remove_duplicates: bool = True) -> Dict[str, Any]:
        """جلب بيانات الشركات من الكاش أولاً، ثم من API إذا لزم الأمر"""
        cache_key = self._get_cache_key(page, limit, remove_duplicates)
        
        # البحث في الكاش أولاً
        cached_data = await redis_cache.get(cache_key)
        if cached_data is not None:
            print(f"✅ تم جلب بيانات الشركات من الكاش - الصفحة {page}")
            
            # إذا كانت البيانات dict، ارجعها مباشرة
            if isinstance(cached_data, dict):
                return cached_data
            # إذا كانت string، حاول تحليلها
            elif isinstance(cached_data, str):
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    print(f"❌ خطأ في تحليل بيانات الكاش لـ {cache_key}")
        
        print(f"🔍 بيانات الشركات غير موجودة في الكاش، جلب من API...")
        
        # جلب البيانات من API
        companies_data = await self._fetch_companies_from_api(
            page=page, 
            limit=limit, 
            remove_duplicates=remove_duplicates
        )
        
        # تخزين البيانات في الكاش
        await redis_cache.set(
            cache_key, 
            companies_data,
            expire=self.cache_expire
        )
        
        print(f"💾 تم تخزين بيانات الشركات في الكاش - الصفحة {page}")
        return companies_data
    
    async def get_company_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """البحث عن شركة بالرمز من الكاش أولاً"""
        cache_key = self._get_symbol_cache_key(symbol)
        
        # البحث في الكاش أولاً
        cached_company = await redis_cache.get(cache_key)
        if cached_company is not None:
            print(f"✅ تم جلب بيانات الشركة {symbol} من الكاش")
            
            # معالجة أنواع البيانات المختلفة
            if isinstance(cached_company, dict):
                return cached_company
            elif isinstance(cached_company, str):
                try:
                    return json.loads(cached_company)
                except json.JSONDecodeError:
                    print(f"❌ خطأ في تحليل بيانات الشركة من الكاش: {symbol}")
        
        print(f"🔍 الشركة {symbol} غير موجودة في الكاش، البحث في API...")
        
        # البحث في API
        result = await self._fetch_companies_from_api(page=1, limit=500, remove_duplicates=True)
        companies = result["data"]
        
        clean_target_symbol = clean_company_symbol(symbol)
        company = None
        
        for comp in companies:
            comp_clean_symbol = clean_company_symbol(comp['symbol'])
            if clean_target_symbol == comp_clean_symbol:
                company = comp
                break
        
        if company:
            # تخزين الشركة في الكاش
            await redis_cache.set(
                cache_key, 
                company,
                expire=self.cache_expire
            )
            print(f"💾 تم تخزين بيانات الشركة {symbol} في الكاش")
        
        return company
    
    async def clear_companies_cache(self):
        """مسح كاش الشركات"""
        print("🧹 جاري مسح كاش الشركات...")
        await redis_cache.flush_all()

# إنشاء نسخة عامة
company_cache = CompanyCache()