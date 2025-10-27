# import json
# import hashlib
# from datetime import datetime, timedelta
# from typing import Dict, List, Any, Optional
# from sqlalchemy.orm import Session
# from app.core.database import get_db
# from app.models.cache import ApiCache
# from app.models.financials import IncomeStatement, BalanceSheet, CashFlow

# class PostgresCache:
#     def __init__(self):
#         self.cache_ttl_hours = 24  # 24 ساعة
    
#     def _generate_cache_key(self, symbol: str, data_type: str, period: str = "annual", limit: int = 6) -> str:
#         """إنشاء مفتاح cache فريد"""
#         key_data = f"{symbol}:{data_type}:{period}:{limit}"
#         key_hash = hashlib.md5(key_data.encode()).hexdigest()
#         return f"pg_cache:{key_hash}"
    
#     def _is_cache_valid(self, cache_entry: ApiCache) -> bool:
#         """التحقق إذا الـ cache entry لسة صالحة"""
#         return cache_entry.expires_at > datetime.utcnow()
    
#     async def get_income_statement(self, symbol: str, period: str = "annual", limit: int = 6) -> Optional[Dict[str, Any]]:
#         """جلب قائمة الدخل من الـ cache أو قاعدة البيانات"""
#         try:
#             clean_symbol = symbol.upper().strip()
#             cache_key = self._generate_cache_key(clean_symbol, "income", period, limit)
            
#             db: Session = next(get_db())
            
#             # البحث في جدول الـ cache
#             cache_entry = db.query(ApiCache).filter(
#                 ApiCache.cache_key == cache_key,
#                 ApiCache.data_type == "income",
#                 ApiCache.symbol == clean_symbol
#             ).first()
            
#             if cache_entry and self._is_cache_valid(cache_entry):
#                 print(f"✅ تم العثور على قائمة الدخل في الـ cache: {clean_symbol}")
#                 return json.loads(cache_entry.cache_data)
            
#             # إذا مافيش في الـ cache، جلب من قاعدة البيانات المالية
#             income_data = db.query(IncomeStatement).filter(
#                 IncomeStatement.symbol == clean_symbol
#             ).order_by(IncomeStatement.fiscal_date.desc()).limit(limit).all()
            
#             if income_data:
#                 # تحويل البيانات إلى dictionary
#                 statements = []
#                 for statement in income_data:
#                     statement_dict = {
#                         "symbol": statement.symbol,
#                         "fiscal_date": statement.fiscal_date.isoformat() if statement.fiscal_date else None,
#                         "year": statement.year,
#                         "quarter": statement.quarter,
#                         "revenue": statement.revenue or statement.sales,
#                         "gross_profit": statement.gross_profit,
#                         "operating_income": statement.operating_income,
#                         "net_income": statement.net_income,
#                         "eps_basic": statement.eps_basic,
#                         "ebit": statement.ebit,
#                         "ebitda": statement.ebitda
#                     }
#                     statements.append({k: v for k, v in statement_dict.items() if v is not None})
                
#                 result = {
#                     "symbol": clean_symbol,
#                     "income_statement": statements,
#                     "period": period,
#                     "limit": limit,
#                     "source": "database"
#                 }
                
#                 # تخزين في الـ cache
#                 await self._store_in_cache(cache_key, "income", clean_symbol, period, limit, result)
                
#                 print(f"✅ تم العثور على قائمة الدخل في قاعدة البيانات: {clean_symbol}")
#                 return result
            
#             return None
            
#         except Exception as e:
#             print(f"❌ خطأ في get_income_statement: {e}")
#             return None
    
#     async def get_balance_sheet(self, symbol: str, period: str = "annual", limit: int = 6) -> Optional[Dict[str, Any]]:
#         """جلب الميزانية العمومية من الـ cache أو قاعدة البيانات"""
#         try:
#             clean_symbol = symbol.upper().strip()
#             cache_key = self._generate_cache_key(clean_symbol, "balance", period, limit)
            
#             db: Session = next(get_db())
            
#             # البحث في جدول الـ cache
#             cache_entry = db.query(ApiCache).filter(
#                 ApiCache.cache_key == cache_key,
#                 ApiCache.data_type == "balance",
#                 ApiCache.symbol == clean_symbol
#             ).first()
            
#             if cache_entry and self._is_cache_valid(cache_entry):
#                 print(f"✅ تم العثور على الميزانية في الـ cache: {clean_symbol}")
#                 return json.loads(cache_entry.cache_data)
            
#             # جلب من قاعدة البيانات المالية
#             balance_data = db.query(BalanceSheet).filter(
#                 BalanceSheet.symbol == clean_symbol
#             ).order_by(BalanceSheet.fiscal_date.desc()).limit(limit).all()
            
#             if balance_data:
#                 # تحويل البيانات إلى dictionary
#                 sheets = []
#                 for sheet in balance_data:
#                     sheet_dict = {
#                         "symbol": sheet.symbol,
#                         "fiscal_date": sheet.fiscal_date.isoformat() if sheet.fiscal_date else None,
#                         "year": sheet.year,
#                         "assets": {
#                             "cash_and_equivalents": sheet.assets.get('cash_and_equivalents', 0) if sheet.assets else 0,
#                             "inventory": sheet.assets.get('inventory', 0) if sheet.assets else 0,
#                             "total_current_assets": sheet.assets.get('total_current_assets', 0) if sheet.assets else 0,
#                             "total_non_current_assets": sheet.assets.get('total_non_current_assets', 0) if sheet.assets else 0,
#                             "total_assets": sheet.assets.get('total_assets', 0) if sheet.assets else 0
#                         },
#                         "liabilities": {
#                             "total_current_liabilities": sheet.liabilities.get('total_current_liabilities', 0) if sheet.liabilities else 0,
#                             "long_term_debt": sheet.liabilities.get('long_term_debt', 0) if sheet.liabilities else 0,
#                             "total_liabilities": sheet.liabilities.get('total_liabilities', 0) if sheet.liabilities else 0
#                         },
#                         "shareholders_equity": {
#                             "total_equity": sheet.shareholders_equity.get('total_equity', 0) if sheet.shareholders_equity else 0
#                         }
#                     }
#                     sheets.append(sheet_dict)
                
#                 result = {
#                     "symbol": clean_symbol,
#                     "balance_sheet": sheets,
#                     "period": period,
#                     "limit": limit,
#                     "source": "database"
#                 }
                
#                 # تخزين في الـ cache
#                 await self._store_in_cache(cache_key, "balance", clean_symbol, period, limit, result)
                
#                 print(f"✅ تم العثور على الميزانية في قاعدة البيانات: {clean_symbol}")
#                 return result
            
#             return None
            
#         except Exception as e:
#             print(f"❌ خطأ في get_balance_sheet: {e}")
#             return None
    
#     async def get_cash_flow(self, symbol: str, period: str = "annual", limit: int = 6) -> Optional[Dict[str, Any]]:
#         """جلب قائمة التدفقات النقدية من الـ cache أو قاعدة البيانات"""
#         try:
#             clean_symbol = symbol.upper().strip()
#             cache_key = self._generate_cache_key(clean_symbol, "cashflow", period, limit)
            
#             db: Session = next(get_db())
            
#             # البحث في جدول الـ cache
#             cache_entry = db.query(ApiCache).filter(
#                 ApiCache.cache_key == cache_key,
#                 ApiCache.data_type == "cashflow",
#                 ApiCache.symbol == clean_symbol
#             ).first()
            
#             if cache_entry and self._is_cache_valid(cache_entry):
#                 print(f"✅ تم العثور على التدفقات النقدية في الـ cache: {clean_symbol}")
#                 return json.loads(cache_entry.cache_data)
            
#             # جلب من قاعدة البيانات المالية
#             cashflow_data = db.query(CashFlow).filter(
#                 CashFlow.symbol == clean_symbol
#             ).order_by(CashFlow.fiscal_date.desc()).limit(limit).all()
            
#             if cashflow_data:
#                 # تحويل البيانات إلى dictionary
#                 flows = []
#                 for flow in cashflow_data:
#                     flow_dict = {
#                         "symbol": flow.symbol,
#                         "fiscal_date": flow.fiscal_date.isoformat() if flow.fiscal_date else None,
#                         "year": flow.year,
#                         "quarter": flow.quarter,
#                         "operating_activities": {
#                             "net_cash_from_operating": flow.operating_activities.get('net_cash_from_operating', 0) if flow.operating_activities else 0
#                         },
#                         "investing_activities": {
#                             "net_cash_from_investing": flow.investing_activities.get('net_cash_from_investing', 0) if flow.investing_activities else 0
#                         },
#                         "financing_activities": {
#                             "net_cash_from_financing": flow.financing_activities.get('net_cash_from_financing', 0) if flow.financing_activities else 0
#                         },
#                         "net_cash_change": flow.net_cash_change or 0,
#                         "free_cash_flow": flow.free_cash_flow or 0,
#                         "end_cash_position": flow.end_cash_position or 0
#                     }
#                     flows.append(flow_dict)
                
#                 result = {
#                     "symbol": clean_symbol,
#                     "cash_flow": flows,
#                     "period": period,
#                     "limit": limit,
#                     "source": "database"
#                 }
                
#                 # تخزين في الـ cache
#                 await self._store_in_cache(cache_key, "cashflow", clean_symbol, period, limit, result)
                
#                 print(f"✅ تم العثور على التدفقات النقدية في قاعدة البيانات: {clean_symbol}")
#                 return result
            
#             return None
            
#         except Exception as e:
#             print(f"❌ خطأ في get_cash_flow: {e}")
#             return None
    
#     async def _store_in_cache(self, cache_key: str, data_type: str, symbol: str, period: str, limit: int, data: Dict[str, Any]):
#         """تخزين البيانات في جدول الـ cache"""
#         try:
#             db: Session = next(get_db())
#             expires_at = datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)
            
#             # البحث عن cache entry موجودة
#             cache_entry = db.query(ApiCache).filter(ApiCache.cache_key == cache_key).first()
            
#             if cache_entry:
#                 # تحديث البيانات الموجودة
#                 cache_entry.cache_data = json.dumps(data, default=str)
#                 cache_entry.updated_at = datetime.utcnow()
#                 cache_entry.expires_at = expires_at
#             else:
#                 # إضافة entry جديدة
#                 cache_entry = ApiCache(
#                     cache_key=cache_key,
#                     cache_data=json.dumps(data, default=str),
#                     data_type=data_type,
#                     symbol=symbol,
#                     period=period,
#                     limit=limit,
#                     expires_at=expires_at
#                 )
#                 db.add(cache_entry)
            
#             db.commit()
#             print(f"✅ تم تخزين البيانات في الـ cache: {symbol}")
            
#         except Exception as e:
#             print(f"❌ خطأ في تخزين الـ cache: {e}")
#             db.rollback()
    
#     async def store_income_statements(self, symbol: str, statements_data: List[Dict[str, Any]]) -> bool:
#         """تخزين قوائم الدخل في قاعدة البيانات"""
#         try:
#             db: Session = next(get_db())
#             clean_symbol = symbol.upper().strip()
#             stored_count = 0
            
#             for statement_data in statements_data:
#                 # تحويل fiscal_date من string إلى date إذا لزم الأمر
#                 fiscal_date = statement_data.get('fiscal_date')
#                 if fiscal_date and isinstance(fiscal_date, str):
#                     try:
#                         statement_data['fiscal_date'] = datetime.strptime(fiscal_date, '%Y-%m-%d').date()
#                     except:
#                         statement_data['fiscal_date'] = None
                
#                 # البحث عن البيان المالي الموجود
#                 existing_statement = None
#                 if statement_data.get('fiscal_date'):
#                     existing_statement = db.query(IncomeStatement).filter(
#                         IncomeStatement.symbol == clean_symbol,
#                         IncomeStatement.fiscal_date == statement_data.get('fiscal_date')
#                     ).first()
                
#                 if existing_statement:
#                     # تحديث البيانات الموجودة
#                     for key, value in statement_data.items():
#                         if hasattr(existing_statement, key) and value is not None:
#                             setattr(existing_statement, key, value)
#                 else:
#                     # إضافة بيان جديد
#                     new_statement = IncomeStatement(
#                         symbol=clean_symbol,
#                         **{k: v for k, v in statement_data.items() if hasattr(IncomeStatement, k) and v is not None}
#                     )
#                     db.add(new_statement)
                
#                 stored_count += 1
            
#             db.commit()
#             print(f"✅ تم تخزين {stored_count} قائمة دخل للشركة {clean_symbol}")
#             return True
            
#         except Exception as e:
#             print(f"❌ خطأ في store_income_statements: {e}")
#             db.rollback()
#             return False
    
#     # نفس الدوال لـ store_balance_sheets و store_cash_flows
#     async def store_balance_sheets(self, symbol: str, sheets_data: List[Dict[str, Any]]) -> bool:
#         # ... (نفس المنطق)
#         pass
    
#     async def store_cash_flows(self, symbol: str, flows_data: List[Dict[str, Any]]) -> bool:
#         # ... (نفس المنطق)
#         pass
    
#     async def invalidate_cache(self, symbol: str = None) -> bool:
#         """حذف بيانات من الـ cache"""
#         try:
#             db: Session = next(get_db())
            
#             if symbol:
#                 # حذف بيانات شركة محددة
#                 deleted = db.query(ApiCache).filter(ApiCache.symbol == symbol.upper()).delete()
#                 print(f"✅ تم حذف {deleted} cache entry للشركة {symbol}")
#             else:
#                 # حذف كل البيانات من الـ cache
#                 deleted = db.query(ApiCache).delete()
#                 print(f"✅ تم حذف جميع البيانات من الـ cache: {deleted} entries")
            
#             db.commit()
#             return True
            
#         except Exception as e:
#             print(f"❌ خطأ في invalidate_cache: {e}")
#             db.rollback()
#             return False

# # إنشاء instance من الـ cache
# postgres_cache = PostgresCache()