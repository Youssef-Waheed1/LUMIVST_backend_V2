import json
import asyncio
from typing import Dict, Any, Optional, List
from app.core.redis import redis_cache
from app.core.database import get_db
from app.services.database.financial_repository import FinancialRepository

class FinancialCache:
    def __init__(self):
        self.cache_prefix = "financials"
        self.cache_expire = 86400  # 24 ساعة
        self.db_cache_expire = 86400 * 7  # أسبوع للبيانات في DB

    def _get_income_key(self, cache_key: str, period: str, limit: int) -> str:
        """مفتاح كاش لقائمة الدخل مع البلد"""
        return f"{self.cache_prefix}:income:{cache_key}:{period}:{limit}"
    
    def _get_balance_key(self, cache_key: str, period: str, limit: int) -> str:
        """مفتاح كاش للميزانية العمومية مع البلد"""
        return f"{self.cache_prefix}:balance:{cache_key}:{period}:{limit}"
    
    def _get_cash_flow_key(self, cache_key: str, period: str, limit: int) -> str:
        """مفتاح كاش للتدفقات النقدية مع البلد"""
        return f"{self.cache_prefix}:cashflow:{cache_key}:{period}:{limit}"
    
    def _extract_symbol_from_cache_key(self, cache_key: str) -> str:
        """استخراج الرمز من cache_key"""
        return cache_key.split(':')[-1] if ':' in cache_key else cache_key
    
    def _extract_country_from_cache_key(self, cache_key: str) -> str:
        """استخراج البلد من cache_key"""
        return cache_key.split(':')[0] if ':' in cache_key else "Saudi Arabia"
    
    async def _get_db_connection(self):
        """الحصول على اتصال قاعدة بيانات بشكل آمن"""
        try:
            return next(get_db())
        except Exception as e:
            print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
            return None
    
    async def _fetch_income_from_api(self, cache_key: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """استيراد دالة API بشكل ديناميكي مع البلد"""
        from app.services.twelve_data.fundamentals import get_income_statement
        
        symbol = self._extract_symbol_from_cache_key(cache_key)
        country = self._extract_country_from_cache_key(cache_key)
        
        print(f"🌐 جلب قائمة الدخل من API: {symbol} - {country}")
        return await get_income_statement(symbol, country=country, period=period, limit=limit)
    
    async def _fetch_balance_from_api(self, cache_key: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """استيراد دالة API بشكل ديناميكي مع البلد"""
        from app.services.twelve_data.fundamentals import get_balance_sheet
        
        symbol = self._extract_symbol_from_cache_key(cache_key)
        country = self._extract_country_from_cache_key(cache_key)
        
        print(f"🌐 جلب الميزانية العمومية من API: {symbol} - {country}")
        return await get_balance_sheet(symbol, country=country, period=period, limit=limit)
    
    async def _fetch_cash_flow_from_api(self, cache_key: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """استيراد دالة API بشكل ديناميكي مع البلد"""
        from app.services.twelve_data.fundamentals import get_cash_flow
        
        symbol = self._extract_symbol_from_cache_key(cache_key)
        country = self._extract_country_from_cache_key(cache_key)
        
        print(f"🌐 جلب التدفقات النقدية من API: {symbol} - {country}")
        return await get_cash_flow(symbol, country=country, period=period, limit=limit)
        
    
    def _convert_db_income_to_api_format(self, db_records: list) -> Dict[str, Any]:
        """تحويل بيانات قائمة الدخل من قاعدة البيانات إلى تنسيق API"""
        income_statement = []
        for record in db_records:
            income_data = {
                "fiscal_date": record.fiscal_date.isoformat() if record.fiscal_date else None,
                "quarter": record.quarter,
                "year": record.year,
                "sales": record.sales or record.revenue,
                "cost_of_goods": record.cost_of_goods,
                "gross_profit": record.gross_profit,
                "operating_expense": record.operating_expense,
                "operating_income": record.operating_income,
                "non_operating_interest": record.non_operating_interest,
                "other_income_expense": record.other_income_expense,
                "pretax_income": record.pretax_income,
                "income_tax": record.income_tax,
                "net_income": record.net_income,
                "net_income_continuous_operations": record.net_income_continuous_operations,
                "minority_interests": record.minority_interests,
                "preferred_stock_dividends": record.preferred_stock_dividends,
                "eps_basic": record.eps_basic,
                "eps_diluted": record.eps_diluted,
                "basic_shares_outstanding": record.basic_shares_outstanding,
                "diluted_shares_outstanding": record.diluted_shares_outstanding,
                "ebit": record.ebit,
                "ebitda": record.ebitda,
                "additional_data": record.additional_data
            }
            income_statement.append(income_data)
        
        return {
            "income_statement": income_statement, 
            "meta": {"symbol": db_records[0].symbol if db_records else ""}
        }

    def _convert_db_balance_to_api_format(self, db_records: list) -> Dict[str, Any]:
        """تحويل بيانات الميزانية العمومية من قاعدة البيانات إلى تنسيق API"""
        balance_sheet = []
        for record in db_records:
            balance_data = {
                "fiscal_date": record.fiscal_date.isoformat() if record.fiscal_date else None,
                "quarter": record.quarter,
                "year": record.year,
                "assets": record.assets,
                "liabilities": record.liabilities,
                "shareholders_equity": record.shareholders_equity,
                "additional_data": record.additional_data
            }
            balance_sheet.append(balance_data)
        
        return {
            "balance_sheet": balance_sheet, 
            "meta": {"symbol": db_records[0].symbol if db_records else ""}
        }

    def _convert_db_cash_flow_to_api_format(self, db_records: list) -> Dict[str, Any]:
        """تحويل بيانات التدفقات النقدية من قاعدة البيانات إلى تنسيق API"""
        cash_flow = []
        for record in db_records:
            cash_flow_data = {
                "fiscal_date": record.fiscal_date.isoformat() if record.fiscal_date else None,
                "quarter": record.quarter,
                "year": record.year,
                "operating_activities": record.operating_activities,
                "investing_activities": record.investing_activities,
                "financing_activities": record.financing_activities,
                "end_cash_position": record.end_cash_position,
                "income_tax_paid": record.income_tax_paid,
                "interest_paid": record.interest_paid,
                "free_cash_flow": record.free_cash_flow,
                "net_cash_change": record.net_cash_change,
                "additional_data": record.additional_data
            }
            cash_flow.append(cash_flow_data)
        
        return {
            "cash_flow": cash_flow, 
            "meta": {"symbol": db_records[0].symbol if db_records else ""}
        }

    async def _get_repository(self):
        """الحصول على repository مع جلسة قاعدة بيانات"""
        db = next(get_db())
        return FinancialRepository(db)
    
    async def get_income_statement(self, cache_key: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """جلب قائمة الدخل - Cache Hierarchy: Redis → PostgreSQL → API"""
        redis_key = self._get_income_key(cache_key, period, limit)
        symbol = self._extract_symbol_from_cache_key(cache_key)
        country = self._extract_country_from_cache_key(cache_key)
        
        # 1. ✅ البحث في Redis أولاً (الأسرع)
        cached_data = await redis_cache.get(redis_key)
        if cached_data is not None:
            print(f"✅ تم جلب قائمة الدخل لـ {cache_key} من الكاش")
            return cached_data
        
        # 2. 🔍 البحث في PostgreSQL (المخزن الدائم)
        print(f"🔍 البحث عن قائمة الدخل لـ {cache_key} في قاعدة البيانات...")
        db = None
        try:
            db = await self._get_db_connection()
            if db:
                repo = FinancialRepository(db)
                db_records = await repo.get_income_statement(symbol, country, period, limit)
                
                if db_records:
                    print(f"✅ تم جلب قائمة الدخل لـ {cache_key} من قاعدة البيانات")
                    db_data = self._convert_db_income_to_api_format(db_records)
                    
                    # تخزين في الكاش للمرة القادمة
                    await redis_cache.set(redis_key, db_data, expire=self.db_cache_expire)
                    return db_data
                    
        except Exception as e:
            print(f"⚠️ فشل جلب البيانات من PostgreSQL: {e}")
        finally:
            if db:
                db.close()
        
        # 3. 🌐 جلب من API (المصدر الخارجي)
        print(f"🌐 قائمة الدخل لـ {cache_key} غير موجودة محلياً، جلب من API...")
        try:
            api_data = await self._fetch_income_from_api(cache_key, period=period, limit=limit)
            
            if api_data and api_data.get('income_statement'):
                print(f"💾 حفظ قائمة الدخل لـ {cache_key} في قاعدة البيانات...")
                
                # حفظ في PostgreSQL
                db = await self._get_db_connection()
                if db:
                    try:
                        repo = FinancialRepository(db)
                        await repo.save_bulk_income_statements(symbol, country, api_data['income_statement'])
                        print(f"💾 تم حفظ قائمة الدخل لـ {cache_key} في PostgreSQL")
                    except Exception as e:
                        print(f"⚠️ فشل حفظ البيانات في PostgreSQL: {e}")
                    finally:
                        if db:
                            db.close()
                
                # تخزين في Redis
                await redis_cache.set(redis_key, api_data, expire=self.cache_expire)
                print(f"💾 تم تخزين قائمة الدخل لـ {cache_key} في الكاش وقاعدة البيانات")
            else:
                print(f"⚠️ لا توجد بيانات قائمة دخل لـ {cache_key} من API")
                api_data = {"income_statement": [], "meta": {"symbol": symbol}}
            
            return api_data
                
        except Exception as e:
            print(f"❌ خطأ في جلب البيانات من API: {e}")
            error_data = {"income_statement": [], "meta": {"symbol": symbol}}
            return error_data
    
    async def get_balance_sheet(self, cache_key: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """جلب الميزانية العمومية - Cache Hierarchy: Redis → PostgreSQL → API"""
        redis_key = self._get_balance_key(cache_key, period, limit)
        symbol = self._extract_symbol_from_cache_key(cache_key)
        country = self._extract_country_from_cache_key(cache_key)
        
        # 1. ✅ البحث في Redis أولاً
        cached_data = await redis_cache.get(redis_key)
        if cached_data is not None:
            print(f"✅ تم جلب الميزانية العمومية لـ {cache_key} من الكاش")
            return cached_data
        
        # 2. 🔍 البحث في PostgreSQL
        print(f"🔍 البحث عن الميزانية العمومية لـ {cache_key} في قاعدة البيانات...")
        db = None
        try:
            db = await self._get_db_connection()
            if db:
                repo = FinancialRepository(db)
                db_records = await repo.get_balance_sheet(symbol, country, period, limit)
                
                if db_records:
                    print(f"✅ تم جلب الميزانية العمومية لـ {cache_key} من قاعدة البيانات")
                    db_data = self._convert_db_balance_to_api_format(db_records)
                    
                    await redis_cache.set(redis_key, db_data, expire=self.db_cache_expire)
                    return db_data
                    
        except Exception as e:
            print(f"⚠️ فشل جلب البيانات من PostgreSQL: {e}")
        finally:
            if db:
                db.close()
        
        # 3. 🌐 جلب من API
        print(f"🌐 الميزانية العمومية لـ {cache_key} غير موجودة محلياً، جلب من API...")
        try:
            api_data = await self._fetch_balance_from_api(cache_key, period=period, limit=limit)
            
            if api_data and api_data.get('balance_sheet'):
                print(f"💾 حفظ الميزانية العمومية لـ {cache_key} في قاعدة البيانات...")
                
                db = await self._get_db_connection()
                if db:
                    try:
                        repo = FinancialRepository(db)
                        await repo.save_bulk_balance_sheets(symbol, country, api_data['balance_sheet'])
                        print(f"💾 تم حفظ الميزانية العمومية لـ {cache_key} في PostgreSQL")
                    except Exception as e:
                        print(f"⚠️ فشل حفظ البيانات في PostgreSQL: {e}")
                    finally:
                        if db:
                            db.close()
                
                await redis_cache.set(redis_key, api_data, expire=self.cache_expire)
                print(f"💾 تم تخزين الميزانية العمومية لـ {cache_key} في الكاش وقاعدة البيانات")
            else:
                print(f"⚠️ لا توجد بيانات ميزانية عمومية لـ {cache_key} من API")
                api_data = {"balance_sheet": [], "meta": {"symbol": symbol}}
            
            return api_data
            
        except Exception as e:
            print(f"❌ خطأ في جلب البيانات من API: {e}")
            error_data = {"balance_sheet": [], "meta": {"symbol": symbol}}
            return error_data
    
    async def get_cash_flow(self, cache_key: str, period: str = "annual", limit: int = 6) -> Dict[str, Any]:
        """جلب التدفقات النقدية - Cache Hierarchy: Redis → PostgreSQL → API"""
        redis_key = self._get_cash_flow_key(cache_key, period, limit)
        symbol = self._extract_symbol_from_cache_key(cache_key)
        country = self._extract_country_from_cache_key(cache_key)
        
        # 1. ✅ البحث في Redis أولاً
        cached_data = await redis_cache.get(redis_key)
        if cached_data is not None:
            print(f"✅ تم جلب التدفقات النقدية لـ {cache_key} من الكاش")
            return cached_data
        
        # 2. 🔍 البحث في PostgreSQL
        print(f"🔍 البحث عن التدفقات النقدية لـ {cache_key} في قاعدة البيانات...")
        db = None
        try:
            db = await self._get_db_connection()
            if db:
                repo = FinancialRepository(db)
                db_records = await repo.get_cash_flow(symbol, country, period, limit)
                
                if db_records:
                    print(f"✅ تم جلب التدفقات النقدية لـ {cache_key} من قاعدة البيانات")
                    db_data = self._convert_db_cash_flow_to_api_format(db_records)
                    
                    await redis_cache.set(redis_key, db_data, expire=self.db_cache_expire)
                    return db_data
                    
        except Exception as e:
            print(f"⚠️ فشل جلب البيانات من PostgreSQL: {e}")
        finally:
            if db:
                db.close()
        
        # 3. 🌐 جلب من API
        print(f"🌐 التدفقات النقدية لـ {cache_key} غير موجودة محلياً، جلب من API...")
        try:
            api_data = await self._fetch_cash_flow_from_api(cache_key, period=period, limit=limit)
            
            if api_data and api_data.get('cash_flow'):
                print(f"💾 حفظ التدفقات النقدية لـ {cache_key} في قاعدة البيانات...")
                
                db = await self._get_db_connection()
                if db:
                    try:
                        repo = FinancialRepository(db)
                        await repo.save_bulk_cash_flows(symbol, country, api_data['cash_flow'])
                        print(f"💾 تم حفظ التدفقات النقدية لـ {cache_key} في PostgreSQL")
                    except Exception as e:
                        print(f"⚠️ فشل حفظ البيانات في PostgreSQL: {e}")
                    finally:
                        if db:
                            db.close()
                
                await redis_cache.set(redis_key, api_data, expire=self.cache_expire)
                print(f"💾 تم تخزين التدفقات النقدية لـ {cache_key} في الكاش وقاعدة البيانات")
            else:
                print(f"⚠️ لا توجد بيانات تدفقات نقدية لـ {cache_key} من API")
                api_data = {"cash_flow": [], "meta": {"symbol": symbol}}
            
            return api_data
            
        except Exception as e:
            print(f"❌ خطأ في جلب البيانات من API: {e}")
            error_data = {"cash_flow": [], "meta": {"symbol": symbol}}
            return error_data

    async def clear_financial_cache(self, symbol: str = None, country: str = "Saudi Arabia"):
        """مسح كاش البيانات المالية لرمز واحد أو رموز متعددة مع البلد"""
        try:
            print(f"🔍 بدء مسح كاش البيانات المالية لـ: {symbol} - البلد: {country}")
            
            if not await redis_cache.ensure_connection():
                raise Exception("لا يمكن الاتصال بـ Redis")

            if symbol:
                if ',' in symbol:
                    symbol_list = [s.strip() for s in symbol.split(',')]
                    deleted_count = 0
                    for sym in symbol_list:
                        cache_key = f"{country}:{sym}"
                        patterns = [
                            f"{self.cache_prefix}:income:{cache_key}:*",
                            f"{self.cache_prefix}:balance:{cache_key}:*", 
                            f"{self.cache_prefix}:cashflow:{cache_key}:*"
                        ]
                        for pattern in patterns:
                            keys = await redis_cache.keys(pattern)
                            print(f"🔍 المفاتيح الموجودة للنمط {pattern}: {keys}")
                            if keys:
                                for key in keys:
                                    await redis_cache.delete(key)
                                    deleted_count += 1
                                    print(f"🗑️ تم حذف المفتاح: {key}")
                    print(f"🧹 تم مسح كاش البيانات المالية لـ {len(symbol_list)} رمز في {country}")
                    return deleted_count
                else:
                    cache_key = f"{country}:{symbol}"
                    patterns = [
                        f"{self.cache_prefix}:income:{cache_key}:*",
                        f"{self.cache_prefix}:balance:{cache_key}:*", 
                        f"{self.cache_prefix}:cashflow:{cache_key}:*"
                    ]
                    
                    deleted_count = 0
                    for pattern in patterns:
                        keys = await redis_cache.keys(pattern)
                        print(f"🔍 المفاتيح الموجودة للنمط {pattern}: {keys}")
                        if keys:
                            for key in keys:
                                await redis_cache.delete(key)
                                deleted_count += 1
                                print(f"🗑️ تم حذف المفتاح: {key}")
                    
                    print(f"✅ تم مسح {deleted_count} مفتاح لـ {cache_key}")
                    return deleted_count
            else:
                await redis_cache.flush_all()
                print("🧹 تم مسح كل كاش البيانات المالية")
                return "all"
        except Exception as e:
            print(f"❌ خطأ في مسح كاش البيانات المالية: {e}")
            import traceback
            traceback.print_exc()
            raise e

# إنشاء نسخة عامة
financial_cache = FinancialCache()