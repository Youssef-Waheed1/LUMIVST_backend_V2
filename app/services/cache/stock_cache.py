import json
import math
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.core.redis import redis_cache
from app.core.database import get_db
from app.services.twelve_data.profile_service import get_company_profile
from app.services.twelve_data.quote_service import get_stock_quote, _calculate_turnover
from app.schemas.stock import StockResponse

def clean_symbol(symbol: str) -> str:
    """تنظيف الرمز للإنتاج"""
    if not symbol:
        return ""
    return ''.join(filter(str.isdigit, symbol)).upper()

# ⭐ قائمة الرموز السعودية
SAUDI_STOCKS = {
                        "1010", "1020", "1030", "1050", "1060", "1080", "1111", "1120", "1140", 
                        "1150", "1180", "1182", "1183", "1201", "1202", "1210", "1211", "1212",
                        "1213", "1214", "1301", "1302", "1303", "1304", "1320", "1321", "1322",
                        "1323", "1810", "1820", "1830", "1831", "1832", "1833", "2001", "2010", 
                        "2020", "2030", "2040", "2050", "2060", "2070", "2080", "2081", "2082",
                        "2083", "2090", "2100", "2110", "2120", "2130", "2140", "2150", "2160", 
                        "2170", "2180", "2190", "2200", "2210", "2220", "2222", "2223", "2230", 
                        "2240", "2250", "2270", "2280", "2281", "2282", "2283", "2284", "2285", 
                        "2286", "2287", "2290", "2300", "2310", "2320", "2330", "2340", "2350", 
                        "2360", "2370", "2380", "2381", "2382", "3002", "3003", "3004", 
                        "3005", "3007", "3008", "3010", "3020", "3030", "3040", "3050", "3060",
                        "3080", "3090", "3091", "3092", "4001", "4002", "4003", "4004", "4005",
                        "4006", "4007", "4008", "4009", "4011", "4012", "4013", "4014", 
                        "4015", "4016", "4017", "4018", "4019", "4020", "4030", "4031", "4040", 
                        "4050", "4061", "4070", "4071", "4072", "4080", "4081", "4082", "4083", 
                        "4084", "4090", "4100", "4110", "4130", "4140", "4141", "4142", "4143", 
                        "4144", "4145", "4146", "4150", "4160", "4161", "4162", "4163", "4164", 
                        "4165", "4170", "4180", "4190", "4191", "4192", "4193", "4194", "4200", 
                        "4210", "4220", "4230", "4240", "4250", "4260", "4261", "4262", "4263", 
                        "4264", "4270", "4280", "4290", "4291", "4292", "4300", "4310", "4320", 
                        "4321", "4322", "4323", "4324", "4325", "4326", "4330", "4331", "4332", 
                        "4333", "4334", "4335", "4336", "4337", "4338", "4339", "4340", "4342", 
                        "4344", "4345", "4346", "4347", "4348", "4349", "4350", "5110", "6010", 
                        "6012", "6013", "6014", "6015", "6016", "6017", "6018", "6020", "6040", 
                        "6050", "6060", "6070", "6090", "7010", "7020", "7030", "7200", 
                        "7201", "7202", "7203", "7204", "7211", "8010", "8012", "8020", "8030", 
                        "8040", "8050", "8060", "8070", "8100", "8120", "8150", "8160", "8170", 
                        "8180", "8190", "8200", "8210", "8230", "8240", "8250", "8260", "8280", 
                        "8300", "8310", "8311", "8313","6004","1835","1834","6002","4051","6001",
                        "4021","7040","2084"
            
}

class StockCache:
    def __init__(self):
        self.cache_prefix = "tadawul_stocks"
        self.cache_expire = 300
        self.all_cache_expire = 600
        self.db_cache_expire = 3600
    
    def _get_cache_key(self, page: int, limit: int, country: str = "Saudi Arabia") -> str:
        return f"{self.cache_prefix}:page:{page}:limit:{limit}:country:{country}"
    
    def _get_all_cache_key(self, country: str = "Saudi Arabia") -> str:
        return f"{self.cache_prefix}:all:country:{country}"
    
    def _get_symbol_cache_key(self, symbol: str, country: str = "Saudi Arabia") -> str:
        clean_symbol_val = clean_symbol(symbol)
        return f"{self.cache_prefix}:symbol:{clean_symbol_val}:country:{country}"
    
    def _get_bulk_cache_key(self, symbols: List[str], country: str = "Saudi Arabia") -> str:
        """مفتاح cache جديد للطلبات الجماعية"""
        symbols_hash = hash(tuple(sorted(symbols)))
        return f"{self.cache_prefix}:bulk:{symbols_hash}:country:{country}"
    
    async def _get_db_connection(self):
        """الحصول على اتصال قاعدة بيانات بشكل آمن"""
        try:
            return next(get_db())
        except Exception as e:
            print(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
            return None
    
    async def _save_to_postgresql(self, symbol: str, profile_data: Dict, quote_data: Dict):
        """حفظ البيانات في PostgreSQL"""
        db = None
        try:
            db = await self._get_db_connection()
            if not db:
                return
                
            # حفظ Profile
            if profile_data:
                from app.models.profile import CompanyProfile
                existing_profile = db.query(CompanyProfile).filter(CompanyProfile.symbol == symbol).first()
                
                if existing_profile:
                    # تحديث البيانات
                    for key, value in profile_data.items():
                        if hasattr(existing_profile, key) and value is not None:
                            setattr(existing_profile, key, value)
                else:
                    # إنشاء جديد
                    profile = CompanyProfile(
                        symbol=symbol,
                        name=profile_data.get("name", "N/A"),
                        exchange=profile_data.get("exchange", "Tadawul"),
                        sector=profile_data.get("sector"),
                        industry=profile_data.get("industry"),
                        employees=profile_data.get("employees"),
                        website=profile_data.get("website"),
                        description=profile_data.get("description"),
                        state=profile_data.get("state"),
                        country=profile_data.get("country", "Saudi Arabia")
                    )
                    db.add(profile)
            
            # حفظ Quote - ⭐⭐ التصحيح هنا
            if quote_data:
                from app.models.quote import StockQuote
                existing_quote = db.query(StockQuote).filter(StockQuote.symbol == symbol).first()
                
                # استخراج بيانات 52 أسبوع
                fifty_two_week = quote_data.get("fifty_two_week", {})
                
                quote_update_data = {
                    "symbol": symbol,
                    "currency": quote_data.get("currency", "SAR"),
                    "datetime": quote_data.get("datetime"),
                    "timestamp": quote_data.get("timestamp"),
                    "open": quote_data.get("open"),
                    "high": quote_data.get("high"),
                    "low": quote_data.get("low"),
                    "close": quote_data.get("close"),
                    "volume": quote_data.get("volume"),
                    "previous_close": quote_data.get("previous_close"),
                    "change": quote_data.get("change"),
                    "percent_change": quote_data.get("percent_change"),
                    "average_volume": quote_data.get("average_volume"),
                    "is_market_open": quote_data.get("is_market_open", False),
                    
                    # ⭐⭐ حفظ كل حقول 52 أسبوع
                    "fifty_two_week_low": self._parse_float(fifty_two_week.get("low")),
                    "fifty_two_week_high": self._parse_float(fifty_two_week.get("high")),
                    "fifty_two_week_low_change": self._parse_float(fifty_two_week.get("low_change")),
                    "fifty_two_week_high_change": self._parse_float(fifty_two_week.get("high_change")),
                    "fifty_two_week_low_change_percent": self._parse_float(fifty_two_week.get("low_change_percent")),
                    "fifty_two_week_high_change_percent": self._parse_float(fifty_two_week.get("high_change_percent")),
                    "fifty_two_week_range": fifty_two_week.get("range")
                }
                
                if existing_quote:
                    # تحديث البيانات
                    for key, value in quote_update_data.items():
                        if hasattr(existing_quote, key) and value is not None:
                            setattr(existing_quote, key, value)
                else:
                    # إنشاء جديد
                    quote = StockQuote(**quote_update_data)
                    db.add(quote)
            
            db.commit()
            print(f"💾 تم حفظ بيانات {symbol} في PostgreSQL")
            
        except Exception as e:
            print(f"❌ خطأ في حفظ البيانات في PostgreSQL: {e}")
            if db:
                db.rollback()
        finally:
            if db:
                db.close()

    def _parse_float(self, value):
        """دالة مساعدة لتحويل القيم إلى float"""
        if value in [None, "N/A", ""]:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def _combine_stock_data(self, profile_data: Dict[str, Any], quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """دمج بيانات Profile و Quote"""
        
        def parse_value(value):
            if value in [None, "N/A", ""]:
                return None
            return value
        
        def parse_float(value):
            if value in [None, "N/A", ""]:
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        # ⭐⭐ بناء بيانات 52 أسبوع من قاعدة البيانات
        fifty_two_week_data = {
            "low": parse_float(quote_data.get("fifty_two_week_low")),
            "high": parse_float(quote_data.get("fifty_two_week_high")),
            "low_change": parse_float(quote_data.get("fifty_two_week_low_change")),
            "high_change": parse_float(quote_data.get("fifty_two_week_high_change")),
            "low_change_percent": parse_float(quote_data.get("fifty_two_week_low_change_percent")),
            "high_change_percent": parse_float(quote_data.get("fifty_two_week_high_change_percent")),
            "range": parse_value(quote_data.get("fifty_two_week_range"))
        }
        
        return {
            "symbol": profile_data.get("symbol") or quote_data.get("symbol"),
            "name": profile_data.get("name", "N/A"),
            "exchange": profile_data.get("exchange", "Tadawul"),
            "sector": parse_value(profile_data.get("sector")),
            "industry": parse_value(profile_data.get("industry")),
            "employees": parse_value(profile_data.get("employees")),
            "website": parse_value(profile_data.get("website")),
            "description": parse_value(profile_data.get("description")),
            "state": parse_value(profile_data.get("state")),
            "country": parse_value(profile_data.get("country", "Saudi Arabia")),
            "currency": quote_data.get("currency", "SAR"),
            "price": parse_float(quote_data.get("close")),
            "change": parse_float(quote_data.get("change")),
            "change_percent": parse_float(quote_data.get("percent_change")),
            "previous_close": parse_float(quote_data.get("previous_close")),
            "volume": parse_value(quote_data.get("volume")),
            "turnover": _calculate_turnover(quote_data.get("volume"), quote_data.get("close")),
            "open": parse_float(quote_data.get("open")),
            "high": parse_float(quote_data.get("high")),
            "low": parse_float(quote_data.get("low")),
            "average_volume": parse_value(quote_data.get("average_volume")),
            "is_market_open": quote_data.get("is_market_open", False),
            
            # ⭐⭐ التصحيح: استخدام البيانات المدمجة
            "fifty_two_week": fifty_two_week_data,
            "fifty_two_week_range": parse_value(quote_data.get("fifty_two_week_range")),
            "fifty_two_week_low": parse_float(quote_data.get("fifty_two_week_low")),
            "fifty_two_week_high": parse_float(quote_data.get("fifty_two_week_high")),
            "fifty_two_week_low_change": parse_float(quote_data.get("fifty_two_week_low_change")),
            "fifty_two_week_high_change": parse_float(quote_data.get("fifty_two_week_high_change")),
            "fifty_two_week_low_change_percent": parse_float(quote_data.get("fifty_two_week_low_change_percent")),
            "fifty_two_week_high_change_percent": parse_float(quote_data.get("fifty_two_week_high_change_percent")),
            
            "last_updated": datetime.now().isoformat()
        }
    
    async def clear_symbols_cache(self, symbols: List[str], clear_db: bool = False):
        """مسح كاش رموز محددة"""
        cleared_count = 0
        
        for symbol in symbols:
            clean_sym = clean_symbol(symbol)
            
            # مسح من Redis
            cache_key = self._get_symbol_cache_key(clean_sym, "Saudi Arabia")
            await redis_cache.delete(cache_key)
            
            # مسح من قاعدة البيانات إذا طلب
            if clear_db:
                db = None
                try:
                    db = await self._get_db_connection()
                    if db:
                        from app.models.profile import CompanyProfile
                        from app.models.quote import StockQuote
                        
                        # حذف البيانات
                        db.query(CompanyProfile).filter(CompanyProfile.symbol == clean_sym).delete()
                        db.query(StockQuote).filter(StockQuote.symbol == clean_sym).delete()
                        db.commit()
                        
                        print(f"🗑️ تم حذف بيانات {clean_sym} من PostgreSQL")
                except Exception as e:
                    print(f"⚠️ خطأ في حذف {clean_sym} من PostgreSQL: {e}")
                    if db:
                        db.rollback()
                finally:
                    if db:
                        db.close()
            
            cleared_count += 1
            print(f"🧹 تم مسح كاش {clean_sym}")
        
        return cleared_count
    
    async def get_bulk_stocks_data(self, symbols: List[str], country: str = "Saudi Arabia") -> Dict[str, Any]:
        """جلب بيانات مجموعة من الرموز مرة واحدة"""
        cache_key = self._get_bulk_cache_key(symbols, country)
        
        # 1. ✅ البحث في Redis أولاً
        cached_data = await redis_cache.get(cache_key)
        if cached_data and isinstance(cached_data, dict):
            print(f"✅ تم جلب بيانات {len(symbols)} سهم من Redis")
            return cached_data
        
        # 2. 🌐 جلب من API
        print(f"🌐 جلب بيانات {len(symbols)} سهم من API...")
        
        all_stocks = []
        BATCH_SIZE = 50 # حجم الدفعة
        
        for i in range(0, len(symbols), BATCH_SIZE):
            batch_symbols = symbols[i:i + BATCH_SIZE]
            
            # إنشاء tasks لكل سهم في الدفعة
            tasks = []
            for symbol in batch_symbols:
                tasks.append(self.get_stock_by_symbol(symbol, country))
            
            # تنفيذ الدفعة
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(results):
                symbol = batch_symbols[j]
                if isinstance(result, Exception):
                    print(f"⚠️ خطأ في معالجة السهم {symbol}: {result}")
                    continue
                if result:
                    all_stocks.append(result)
                else:
                    print(f"⚠️ لا توجد بيانات للرمز {symbol}")
            
            # delay بين الدفعات
            if i + BATCH_SIZE < len(symbols):
                await asyncio.sleep(2)
            
            print(f"📊 تقدم: {min(i + BATCH_SIZE, len(symbols))}/{len(symbols)}")
        
        result_data = {
            "data": all_stocks,
            "total": len(all_stocks),
            "symbols_requested": len(symbols),
            "symbols_found": len(all_stocks),
            "country": country,
            "timestamp": datetime.now().isoformat()
        }
        
        # حفظ في Redis
        await redis_cache.set(cache_key, result_data, expire=self.cache_expire)
        print(f"💾 تم تخزين بيانات {len(all_stocks)} سهم في Redis")
        
        return result_data
    
    async def get_all_saudi_stocks(self, country: str = "Saudi Arabia") -> Dict[str, Any]:
        """جلب كل الأسهم السعودية المحددة في SAUDI_STOCKS"""
        symbols_list = list(SAUDI_STOCKS)
        return await self.get_bulk_stocks_data(symbols_list, country)

    async def get_stock_by_symbol(self, symbol: str, country: str = "Saudi Arabia") -> Optional[Dict[str, Any]]:
        """جلب بيانات سهم معين"""
        clean_sym = clean_symbol(symbol)
        cache_key = self._get_symbol_cache_key(clean_sym, country)
        
        # 1. ✅ البحث في Redis أولاً
        cached_stock = await redis_cache.get(cache_key)
        if cached_stock and isinstance(cached_stock, dict):
            print(f"✅ تم جلب بيانات {clean_sym} من Redis")
            return cached_stock
        
        # 2. 🔍 البحث في PostgreSQL
        print(f"🔍 البحث في PostgreSQL للرمز {clean_sym}...")
        db = None
        try:
            db = await self._get_db_connection()
            if db:
                from app.models.profile import CompanyProfile
                from app.models.quote import StockQuote
                
                db_profile = db.query(CompanyProfile).filter(CompanyProfile.symbol == clean_sym).first()
                db_quote = db.query(StockQuote).filter(StockQuote.symbol == clean_sym).first()
                
                if db_profile and db_quote:
                    print(f"✅ تم جلب بيانات {clean_sym} من PostgreSQL")
                    
                    profile_dict = {c.name: getattr(db_profile, c.name) for c in db_profile.__table__.columns}
                    quote_dict = {c.name: getattr(db_quote, c.name) for c in db_quote.__table__.columns}
                    
                    stock_data = await self._combine_stock_data(profile_dict, quote_dict)
                    
                    await redis_cache.set(cache_key, stock_data, expire=self.db_cache_expire)
                    return stock_data
                    
        except Exception as e:
            print(f"⚠️ فشل جلب البيانات من PostgreSQL: {e}")
        finally:
            if db:
                db.close()
        
        # 3. 🌐 جلب من API
        print(f"🌐 جلب بيانات {clean_sym} من API...")
        try:
            profile_task = get_company_profile(clean_sym, country)
            quote_task = get_stock_quote(clean_sym, country)
            
            api_profile, api_quote = await asyncio.gather(profile_task, quote_task)
            
            if not api_profile and not api_quote:
                print(f"❌ لا توجد بيانات للرمز {clean_sym} في API")
                return None
            
# في جزء دمج البيانات من API، غير إلى:
            stock_data = {
                "symbol": clean_sym,
                "name": api_profile.get("name", "N/A") if api_profile else "N/A",
                "exchange": "Tadawul",
                "sector": api_profile.get("sector") if api_profile else "N/A",
                "industry": api_profile.get("industry") if api_profile else "N/A",
                "employees": api_profile.get("employees") if api_profile else "N/A",
                "website": api_profile.get("website") if api_profile else "N/A",
                "country": api_profile.get("country", country) if api_profile else country,
                "state": api_profile.get("state") if api_profile else "N/A",
                "currency": api_quote.get("currency", "SAR") if api_quote else "SAR",
                "price": api_quote.get("close") if api_quote else "N/A",
                "change": api_quote.get("change") if api_quote else "N/A",
                "change_percent": api_quote.get("percent_change") if api_quote else "N/A",
                "previous_close": api_quote.get("previous_close") if api_quote else "N/A",
                "volume": api_quote.get("volume") if api_quote else "N/A",
                "turnover": _calculate_turnover(api_quote.get("volume"), api_quote.get("close")) if api_quote else "N/A",
                "open": api_quote.get("open") if api_quote else "N/A",
                "high": api_quote.get("high") if api_quote else "N/A",
                "low": api_quote.get("low") if api_quote else "N/A",
                "average_volume": api_quote.get("average_volume") if api_quote else "N/A",
                "is_market_open": api_quote.get("is_market_open", False) if api_quote else False,
                
                # ⭐⭐ التصحيح: حفظ بيانات 52 أسبوع كاملة من API
                "fifty_two_week": api_quote.get("fifty_two_week", {}) if api_quote else {},
                "fifty_two_week_range": api_quote.get("fifty_two_week", {}).get("range", "N/A") if api_quote else "N/A",
                "fifty_two_week_low": api_quote.get("fifty_two_week", {}).get("low", "N/A") if api_quote else "N/A",
                "fifty_two_week_high": api_quote.get("fifty_two_week", {}).get("high", "N/A") if api_quote else "N/A",
                "fifty_two_week_low_change": api_quote.get("fifty_two_week", {}).get("low_change", "N/A") if api_quote else "N/A",
                "fifty_two_week_high_change": api_quote.get("fifty_two_week", {}).get("high_change", "N/A") if api_quote else "N/A",
                "fifty_two_week_low_change_percent": api_quote.get("fifty_two_week", {}).get("low_change_percent", "N/A") if api_quote else "N/A",
                "fifty_two_week_high_change_percent": api_quote.get("fifty_two_week", {}).get("high_change_percent", "N/A") if api_quote else "N/A",
                
                "last_updated": datetime.now().isoformat()
            }
            
            # حفظ في PostgreSQL
            try:
                if api_profile or api_quote:
                    await self._save_to_postgresql(clean_sym, api_profile, api_quote)
                    print(f"💾 تم حفظ بيانات {clean_sym} في PostgreSQL")
            except Exception as e:
                print(f"⚠️ فشل حفظ البيانات في PostgreSQL: {e}")
            
            # حفظ في Redis
            await redis_cache.set(cache_key, stock_data, expire=self.cache_expire)
            print(f"💾 تم تخزين بيانات {clean_sym} في Redis")
            
            return stock_data
            
        except Exception as e:
            print(f"❌ خطأ في جلب البيانات من API: {e}")
            return None

    async def get_all_stocks(self, country: str = "Saudi Arabia") -> Dict[str, Any]:
        """جلب كل الأسهم - Cache Hierarchy: Redis → PostgreSQL → API"""
        cache_key = self._get_all_cache_key(country)
        
        # 1. ✅ البحث في Redis أولاً (الأسرع)
        cached_data = await redis_cache.get(cache_key)
        if cached_data and isinstance(cached_data, dict):
            print(f"✅ تم جلب كل أسهم Tadawul من Redis")
            return cached_data
        
        # 2. 🔍 البحث في PostgreSQL (المخزن الدائم)
        print(f"🔍 جلب كل الأسهم من PostgreSQL...")
        db = None
        try:
            db = await self._get_db_connection()
            if db:
                from app.models.profile import CompanyProfile
                from app.models.quote import StockQuote
                
                db_profiles = db.query(CompanyProfile).all()
                db_quotes = db.query(StockQuote).all()
                
                if db_profiles and len(db_profiles) > 0:
                    print(f"✅ تم جلب {len(db_profiles)} شركة من PostgreSQL")
                    
                    # إنشاء lookup dictionaries
                    quotes_dict = {quote.symbol: quote for quote in db_quotes}
                    
                    all_stocks = []
                    for profile in db_profiles:
                        quote = quotes_dict.get(profile.symbol)
                        if quote:
                            profile_dict = {c.name: getattr(profile, c.name) for c in profile.__table__.columns}
                            quote_dict = {c.name: getattr(quote, c.name) for c in quote.__table__.columns}
                            stock_data = await self._combine_stock_data(profile_dict, quote_dict)
                            all_stocks.append(stock_data)
                    
                    result_data = {
                        "data": all_stocks,
                        "total": len(all_stocks),
                        "timestamp": datetime.now().isoformat(),
                        "country": country
                    }
                    
                    # حفظ في Redis للمرة القادمة
                    await redis_cache.set(cache_key, result_data, expire=self.db_cache_expire)
                    return result_data
                    
        except Exception as e:
            print(f"⚠️ فشل جلب البيانات من PostgreSQL: {e}")
        finally:
            if db:
                db.close()
        
        # 3. 🌐 جلب من API (المصدر الخارجي)
        print(f"🌐 جلب كل أسهم Tadawul من API...")
        api_data = await self._get_all_stocks_from_api(country)
        
        if api_data and api_data.get("data"):
            # حفظ في Redis للمرة القادمة
            await redis_cache.set(cache_key, api_data, expire=self.all_cache_expire)
            print(f"💾 تم تخزين كل أسهم Tadawul في Redis")
        
        return api_data if api_data else {"data": [], "total": 0}
    
    async def _get_all_stocks_from_api(self, country: str = "Saudi Arabia") -> Dict[str, Any]:
        """جلب كل الأسهم السعودية من API"""
        try:
            # استخدام القائمة الكاملة للرموز السعودية
            saudi_symbols = list(SAUDI_STOCKS)
            
            print(f"🔍 جلب بيانات {len(saudi_symbols)} سهم سعودي من API...")
            
            all_stocks = []
            BATCH_SIZE = 2  # تخفيض الحجم علشان ما نتعداش rate limit
            
            for i in range(0, len(saudi_symbols), BATCH_SIZE):
                batch_symbols = saudi_symbols[i:i + BATCH_SIZE]
                
                tasks = [self.get_stock_by_symbol(symbol, country) for symbol in batch_symbols]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        print(f"⚠️ خطأ في معالجة السهم: {result}")
                        continue
                    if result:
                        all_stocks.append(result)
                
                # delay بين الـ batches
                if i + BATCH_SIZE < len(saudi_symbols):
                    await asyncio.sleep(3)  # زيادة الـ delay
                    
                print(f"📊 تقدم: {min(i + BATCH_SIZE, len(saudi_symbols))}/{len(saudi_symbols)}")
            
            print(f"✅ تم جلب بيانات {len(all_stocks)} سهم من أصل {len(saudi_symbols)}")
            
            return {
                "data": all_stocks,
                "total": len(all_stocks),
                "timestamp": datetime.now().isoformat(),
                "country": country
            }
            
        except Exception as e:
            print(f"❌ خطأ في جلب كل الأسهم من API: {str(e)}")
            return {"data": [], "total": 0}

    async def clear_all_cache(self):
        """مسح كل كاش الأسهم"""
        try:
            # مسح كل المفاتيح المتعلقة بالأسهم من Redis
            keys = await redis_cache.redis_client.keys(f"{self.cache_prefix}:*")
            if keys:
                await redis_cache.redis_client.delete(*keys)
            print("🧹 تم مسح كل كاش الأسهم من Redis")
            return True
        except Exception as e:
            print(f"❌ خطأ في مسح كاش الأسهم: {e}")
            return False
        

# إنشاء نسخة عامة
stock_cache = StockCache()