# app/services/cache/stock_cache.py

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.redis import redis_cache
from app.core.database import get_db
from app.models.profile import CompanyProfile
from app.models.quote import StockQuote
from app.services.twelve_data.profile_service import get_company_profile
from app.services.twelve_data.quote_service import get_stock_quote, _calculate_turnover
from app.utils.saudi_time import get_saudi_metadata, format_saudi_datetime

# قائمة الرموز السعودية
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
    "8300", "8310", "8311", "8313", "6004", "1835", "1834", "6002", "4051", 
    "6001", "4021", "7040", "2084"
}

def clean_symbol(symbol: str) -> str:
    return ''.join(filter(str.isdigit, symbol)).upper()

class StockCache:
    def __init__(self):
        self.cache_expire = 100  # 5 دقائق
        self.db_cache_expire = 3600  # 1 ساعة

    async def _get_db_session(self) -> Session:
        """الحصول على جلسة DB"""
        return next(get_db())

    async def get_stock_data(self, symbol: str, country: str = "Saudi Arabia") -> Optional[Dict[str, Any]]:
        """
        🎯 الدالة الرئيسية - الترتيب: DB → Redis → API
        """
        clean_sym = clean_symbol(symbol)
        
        # 1. جرب DB أولاً
        stock_data = await self._fetch_from_db(clean_sym)
        if stock_data:
            await self._save_to_redis(clean_sym, stock_data, country)
            return stock_data
        
        # 2. جرب Redis ثانياً
        stock_data = await self._fetch_from_redis(clean_sym, country)
        if stock_data:
            return stock_data
        
        # 3. API كملاحة أخيرة
        stock_data = await self._fetch_from_api(clean_sym, country)
        if stock_data:
            await self._save_to_db_and_redis(clean_sym, stock_data, country)
        
        return stock_data

    async def _fetch_from_db(self, symbol: str) -> Optional[Dict[str, Any]]:
        """🔍 جلب من PostgreSQL"""
        try:
            db = await self._get_db_session()
            
            profile = db.query(CompanyProfile).filter_by(symbol=symbol).first()
            quote = db.query(StockQuote).filter_by(symbol=symbol).first()
            
            if profile and quote:
                return self._merge_profile_quote(profile, quote)
            
            return None
        except Exception as e:
            print(f"⚠️ DB Error: {e}")
            return None
        finally:
            db.close()

    async def _fetch_from_redis(self, symbol: str, country: str) -> Optional[Dict[str, Any]]:
        """🔍 جلب من Redis"""
        try:
            cache_key = f"tadawul:stock:{symbol}:{country}"
            return await redis_cache.get(cache_key)
        except:
            return None

    async def _fetch_from_api(self, symbol: str, country: str) -> Optional[Dict[str, Any]]:
        """🌐 جلب من Twelve Data API"""
        try:
            profile, quote = await asyncio.gather(
                get_company_profile(symbol, country),
                get_stock_quote(symbol, country),
                return_exceptions=True
            )
            
            if isinstance(profile, Exception) or isinstance(quote, Exception):
                return None
            
            return self._build_stock_data(symbol, profile, quote)
        except:
            return None

    def _merge_profile_quote(self, profile: CompanyProfile, quote: StockQuote) -> Dict[str, Any]:
        """دمج بيانات DB إلى شكل موحد مع RS Ratings و Change% والتوقيت السعودي"""
        
        # الحصول على metadata السعودي
        metadata = get_saudi_metadata()
        
        return {
            "symbol": profile.symbol,
            "name": profile.name or profile.symbol,
            "exchange": metadata["exchange"],
            "mic_code": metadata["mic_code"],
            "sector": profile.sector,
            "industry": profile.industry,
            "employees": profile.employees,
            "website": profile.website,
            "country": profile.country or "Saudi Arabia",
            "state": profile.state,
            
            "currency": metadata["currency"],
            "price": quote.close,
            "change": quote.change,
            "percent_change": quote.percent_change,
            "previous_close": quote.previous_close,
            "volume": quote.volume,
            "turnover": _calculate_turnover(quote.volume, quote.close),
            "open": quote.open,
            "high": quote.high,
            "low": quote.low,
            "average_volume": quote.average_volume,
            "is_market_open": quote.is_market_open,
            
            # ⭐ التوقيت السعودي
            "datetime": metadata["datetime"],
            "timestamp": metadata["timestamp"],
            "timezone": metadata["timezone"],
            
            # بيانات 52 أسبوع
            "fifty_two_week": {
                "low": quote.fifty_two_week_low,
                "high": quote.fifty_two_week_high,
                "low_change": quote.fifty_two_week_low_change,
                "high_change": quote.fifty_two_week_high_change,
                "low_change_percent": quote.fifty_two_week_low_change_percent,
                "high_change_percent": quote.fifty_two_week_high_change_percent,
                "range": quote.fifty_two_week_range
            },
            "fifty_two_week_low": quote.fifty_two_week_low,
            "fifty_two_week_high": quote.fifty_two_week_high,
            
            # 🎯 RS Ratings
            "rs_12m": quote.rs_12m,
            "rs_9m": quote.rs_9m,
            "rs_6m": quote.rs_6m,
            "rs_3m": quote.rs_3m,
            "rs_1m": quote.rs_1m,
            "rs_2w": quote.rs_2w,
            "rs_1w": quote.rs_1w,
            
            # ⭐ Change% لكل فترة
            "change_12m": quote.change_12m,
            "change_9m": quote.change_9m,
            "change_6m": quote.change_6m,
            "change_3m": quote.change_3m,
            "change_1m": quote.change_1m,
            "change_2w": quote.change_2w,
            "change_1w": quote.change_1w,
            
            "last_updated": format_saudi_datetime()
        }

    def _build_stock_data(self, symbol: str, profile: dict, quote: dict) -> Dict[str, Any]:
        """بناء البيانات من API response مع التوقيت السعودي"""
        
        # الحصول على metadata السعودي
        metadata = get_saudi_metadata()
        
        return {
            "symbol": symbol,
            "name": profile.get("name", symbol) if profile else symbol,
            "exchange": metadata["exchange"],
            "mic_code": metadata["mic_code"],
            "sector": profile.get("sector") if profile else None,
            "industry": profile.get("industry") if profile else None,
            
            "currency": metadata["currency"],
            "price": quote.get("close") if quote else None,
            "change": quote.get("change") if quote else None,
            "percent_change": quote.get("percent_change") if quote else None,
            "volume": quote.get("volume") if quote else None,
            "turnover": _calculate_turnover(quote.get("volume"), quote.get("close")) if quote else None,
            
            # ⭐ التوقيت السعودي من quote (تم تحويله بالفعل في quote_service)
            "datetime": quote.get("datetime") if quote else metadata["datetime"],
            "timestamp": quote.get("timestamp") if quote else metadata["timestamp"],
            "timezone": metadata["timezone"],
            
            "fifty_two_week": quote.get("fifty_two_week", {}) if quote else {},
            "fifty_two_week_low": quote.get("fifty_two_week_low") if quote else None,
            "fifty_two_week_high": quote.get("fifty_two_week_high") if quote else None,
            
            "last_updated": format_saudi_datetime()
        }

    async def _save_to_db_and_redis(self, symbol: str, data: dict, country: str):
        """حفظ في DB + Redis"""
        await self._save_to_db(symbol, data)
        await self._save_to_redis(symbol, data, country)

    async def _save_to_db(self, symbol: str, data: dict):
        """💾 حفظ في PostgreSQL"""
        try:
            db = await self._get_db_session()
            
            # حفظ/تحديث Profile
            profile_dict = {
                "symbol": symbol,
                "name": data.get("name"),
                "exchange": data.get("exchange", "TADAWUL"),
                "sector": data.get("sector"),
                "industry": data.get("industry"),
                "employees": data.get("employees"),
                "website": data.get("website"),
                "country": data.get("country", "Saudi Arabia"),
                "state": data.get("state"),
            }
            db.merge(CompanyProfile(**profile_dict))
            
            # حفظ/تحديث Quote
            fifty_two_week = data.get("fifty_two_week", {})
            quote_dict = {
                "symbol": symbol,
                "currency": data.get("currency", "SAR"),
                "close": data.get("price"),
                "change": data.get("change"),
                "percent_change": data.get("percent_change"),
                "previous_close": data.get("previous_close"),
                "volume": data.get("volume"),
                "open": data.get("open"),
                "high": data.get("high"),
                "low": data.get("low"),
                "average_volume": data.get("average_volume"),
                "is_market_open": data.get("is_market_open"),
                **{f"fifty_two_week_{k}": v for k, v in fifty_two_week.items()},
                "last_updated": datetime.now()
            }
            db.merge(StockQuote(**quote_dict))
            
            db.commit()
            print(f"✅ Saved {symbol} to DB")
        except Exception as e:
            print(f"❌ DB Save Error: {e}")
            db.rollback()
        finally:
            db.close()

    async def _save_to_redis(self, symbol: str, data: dict, country: str):
        """حفظ في Redis"""
        cache_key = f"tadawul:stock:{symbol}:{country}"
        await redis_cache.set(cache_key, data, expire=self.cache_expire)

    async def get_all_saudi_stocks(self, country: str = "Saudi Arabia") -> Dict[str, Any]:
        """جلب كل الأسهم السعودية مع metadata السعودي"""
        symbols = list(SAUDI_STOCKS)
        
        # cache key للكل
        all_key = f"tadawul:all:{country}"
        
        # جرب Redis أولاً
        cached = await redis_cache.get(all_key)
        if cached:
            return cached
        
        # جلب كل سهم
        stocks = []
        for symbol in symbols:
            stock = await self.get_stock_data(symbol, country)
            if stock:
                stocks.append(stock)
        
        # الحصول على metadata السعودي
        metadata = get_saudi_metadata()
        
        result = {
            "data": stocks,
            "total": len(stocks),
            "metadata": metadata,
            "timestamp": metadata["datetime"],
            "country": country
        }
        
        # خزّن في Redis
        await redis_cache.set(all_key, result, expire=self.cache_expire)
        return result

# إنشاء instance
stock_cache = StockCache()