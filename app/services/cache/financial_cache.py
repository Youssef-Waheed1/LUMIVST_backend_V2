import json
from typing import Dict, Any, Optional
from app.core.redis import redis_cache

class FinancialCache:
    def __init__(self):
        self.cache_prefix = "financials"
        self.cache_expire = 86400  # 24 ساعة
    
    def _get_income_key(self, symbol: str, period: str, limit: int) -> str:
        """مفتاح كاش لقائمة الدخل"""
        clean_symbol = symbol.split('.')[0].upper()
        return f"{self.cache_prefix}:income:{clean_symbol}:{period}:{limit}"
    
    def _get_balance_key(self, symbol: str, period: str, limit: int) -> str:
        """مفتاح كاش للميزانية العمومية"""
        clean_symbol = symbol.split('.')[0].upper()
        return f"{self.cache_prefix}:balance:{clean_symbol}:{period}:{limit}"
    
    def _get_cash_flow_key(self, symbol: str, period: str, limit: int) -> str:
        """مفتاح كاش للتدفقات النقدية"""
        clean_symbol = symbol.split('.')[0].upper()
        return f"{self.cache_prefix}:cashflow:{clean_symbol}:{period}:{limit}"
    
    async def _fetch_income_from_api(self, symbol: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """استيراد دالة API بشكل ديناميكي"""
        from app.services.twelve_data.fundamentals import get_income_statement
        return await get_income_statement(symbol, period=period, limit=limit)
    
    async def _fetch_balance_from_api(self, symbol: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """استيراد دالة API بشكل ديناميكي"""
        from app.services.twelve_data.fundamentals import get_balance_sheet
        return await get_balance_sheet(symbol, period=period, limit=limit)
    
    async def _fetch_cash_flow_from_api(self, symbol: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """استيراد دالة API بشكل ديناميكي"""
        from app.services.twelve_data.fundamentals import get_cash_flow
        return await get_cash_flow(symbol, period=period, limit=limit)
    
    async def get_income_statement(self, symbol: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """جلب قائمة الدخل من الكاش أولاً"""
        cache_key = self._get_income_key(symbol, period, limit)
        
        # البحث في الكاش أولاً
        cached_data = await redis_cache.get(cache_key)
        if cached_data is not None:
            print(f"✅ تم جلب قائمة الدخل لـ {symbol} من الكاش")
            
            # إذا كانت البيانات dict بالفعل (من إصدار سابق)، ارجعها مباشرة
            if isinstance(cached_data, dict):
                return cached_data
            # إذا كانت string، استخدمها كما هي (سيتم معالجتها في الroute)
            return cached_data
        
        print(f"🔍 قائمة الدخل لـ {symbol} غير موجودة في الكاش، جلب من API...")
        
        # جلب البيانات من API
        income_data = await self._fetch_income_from_api(symbol, period=period, limit=limit)
        
        # تخزين في الكاش
        await redis_cache.set(
            cache_key, 
            income_data,  # سيقوم redis_cache بتحويلها إلى JSON تلقائياً
            expire=self.cache_expire
        )
        
        print(f"💾 تم تخزين قائمة الدخل لـ {symbol} في الكاش")
        return income_data
    
    async def get_balance_sheet(self, symbol: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """جلب الميزانية العمومية من الكاش أولاً"""
        cache_key = self._get_balance_key(symbol, period, limit)
        
        # البحث في الكاش أولاً
        cached_data = await redis_cache.get(cache_key)
        if cached_data is not None:
            print(f"✅ تم جلب الميزانية العمومية لـ {symbol} من الكاش")
            
            if isinstance(cached_data, dict):
                return cached_data
            return cached_data
        
        print(f"🔍 الميزانية العمومية لـ {symbol} غير موجودة في الكاش، جلب من API...")
        
        # جلب البيانات من API
        balance_data = await self._fetch_balance_from_api(symbol, period=period, limit=limit)
        
        # تخزين في الكاش
        await redis_cache.set(
            cache_key, 
            balance_data,
            expire=self.cache_expire
        )
        
        print(f"💾 تم تخزين الميزانية العمومية لـ {symbol} في الكاش")
        return balance_data
    
    async def get_cash_flow(self, symbol: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """جلب التدفقات النقدية من الكاش أولاً"""
        cache_key = self._get_cash_flow_key(symbol, period, limit)
        
        # البحث في الكاش أولاً
        cached_data = await redis_cache.get(cache_key)
        if cached_data is not None:
            print(f"✅ تم جلب التدفقات النقدية لـ {symbol} من الكاش")
            
            if isinstance(cached_data, dict):
                return cached_data
            return cached_data
        
        print(f"🔍 التدفقات النقدية لـ {symbol} غير موجودة في الكاش، جلب من API...")
        
        # جلب البيانات من API
        cash_flow_data = await self._fetch_cash_flow_from_api(symbol, period=period, limit=limit)
        
        # تخزين في الكاش
        await redis_cache.set(
            cache_key, 
            cash_flow_data,
            expire=self.cache_expire
        )
        
        print(f"💾 تم تخزين التدفقات النقدية لـ {symbol} في الكاش")
        return cash_flow_data
    
    async def clear_financial_cache(self, symbol: str = None):
        """مسح كاش البيانات المالية"""
        if symbol:
            clean_symbol = symbol.split('.')[0].upper()
            patterns = [
                f"{self.cache_prefix}:income:{clean_symbol}:*",
                f"{self.cache_prefix}:balance:{clean_symbol}:*", 
                f"{self.cache_prefix}:cashflow:{clean_symbol}:*"
            ]
            deleted_count = 0
            for pattern in patterns:
                # هذا تنفيذ مبسط - في الإنتاج يمكن استخدام SCAN
                pass
            print(f"🧹 تم طلب مسح كاش البيانات المالية لـ {symbol}")
        else:
            print("🧹 تم طلب مسح كل كاش البيانات المالية")
        
        # استخدام flush_all كحل سريع
        await redis_cache.flush_all()

# إنشاء نسخة عامة
financial_cache = FinancialCache()