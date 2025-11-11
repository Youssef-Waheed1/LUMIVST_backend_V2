import json
from typing import Optional, Dict, Any, List
from app.core.redis import redis_cache
from app.schemas.statistics import StatisticsResponse

# ⭐ قائمة الرموز السعودية المعتمدة
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

def clean_symbol(symbol: str) -> str:
    """تنظيف الرمز للإنتاج"""
    if not symbol:
        return ""
    return ''.join(filter(str.isdigit, symbol)).upper()

class StatisticsCache:
    def __init__(self):
        self.cache_prefix = "statistics"
        self.cache_expire = 3600  # 1 hour
        self.supported_symbols = SAUDI_STOCKS
    
    def _get_cache_key(self, symbol: str, country: str = "Saudi Arabia") -> str:
        """إنشاء مفتاح الكاش"""
        clean_sym = clean_symbol(symbol)
        return f"{self.cache_prefix}:{clean_sym}:country:{country}"
    
    def _get_bulk_cache_key(self, symbols: List[str], country: str = "Saudi Arabia") -> str:
        """مفتاح cache للطلبات الجماعية"""
        clean_symbols = [clean_symbol(sym) for sym in symbols]
        symbols_hash = hash(tuple(sorted(clean_symbols)))
        return f"{self.cache_prefix}:bulk:{symbols_hash}:country:{country}"
    
    def is_symbol_supported(self, symbol: str) -> bool:
        """التحقق إذا كان الرمز مدعوم"""
        clean_sym = clean_symbol(symbol)
        return clean_sym in self.supported_symbols
    
    def get_supported_symbols(self) -> List[str]:
        """الحصول على قائمة الرموز المدعومة"""
        return list(self.supported_symbols)
    
    async def get(self, symbol: str, country: str = "Saudi Arabia") -> Optional[Dict[str, Any]]:
        """
        جلب بيانات الإحصائيات من الكاش
        """
        if not self.is_symbol_supported(symbol):
            print(f"⚠️ الرمز {symbol} غير مدعوم")
            return None
            
        redis_key = self._get_cache_key(symbol, country)
        cached_data = await redis_cache.get(redis_key)
        
        if cached_data is not None:
            print(f"✅ تم جلب الإحصائيات من الكاش للرمز: {symbol}")
            if isinstance(cached_data, dict):
                return cached_data
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return cached_data
        return None
    
    async def set(self, symbol: str, data: Dict[str, Any], country: str = "Saudi Arabia") -> None:
        """
        تخزين بيانات الإحصائيات في الكاش
        """
        if not self.is_symbol_supported(symbol):
            print(f"⚠️ لا يمكن تخزين بيانات الرمز غير المدعوم: {symbol}")
            return
            
        redis_key = self._get_cache_key(symbol, country)
        await redis_cache.setex(
            redis_key,
            self.cache_expire,
            json.dumps(data)
        )
        print(f"💾 تم تخزين الإحصائيات في الكاش للرمز: {symbol}")
    
    async def get_bulk_statistics(self, symbols: List[str], country: str = "Saudi Arabia") -> Dict[str, Any]:
        """جلب إحصائيات مجموعة من الرموز"""
        # تصفية الرموز المدعومة فقط
        supported_symbols = [sym for sym in symbols if self.is_symbol_supported(sym)]
        unsupported_symbols = [sym for sym in symbols if not self.is_symbol_supported(sym)]
        
        if not supported_symbols:
            return {
                "data": [],
                "supported_symbols": supported_symbols,
                "unsupported_symbols": unsupported_symbols,
                "total_requested": len(symbols),
                "total_supported": len(supported_symbols),
                "message": "لا توجد رموز مدعومة في الطلب"
            }
        
        # البحث في الكاش أولاً
        cache_key = self._get_bulk_cache_key(supported_symbols, country)
        cached_data = await redis_cache.get(cache_key)
        
        if cached_data:
            print(f"✅ تم جلب إحصائيات {len(supported_symbols)} رمز من الكاش")
            return json.loads(cached_data)
        
        # إذا لم تكن في الكاش، ستعيد البيانات الفارغة
        # سيتم ملؤها من قبل service
        return {
            "data": [],
            "supported_symbols": supported_symbols,
            "unsupported_symbols": unsupported_symbols,
            "total_requested": len(symbols),
            "total_supported": len(supported_symbols)
        }
    
    async def set_bulk_statistics(self, symbols: List[str], data: Dict[str, Any], country: str = "Saudi Arabia") -> None:
        """تخزين إحصائيات مجموعة من الرموز"""
        cache_key = self._get_bulk_cache_key(symbols, country)
        await redis_cache.setex(
            cache_key,
            self.cache_expire,
            json.dumps(data)
        )
        print(f"💾 تم تخزين إحصائيات {len(symbols)} رمز في الكاش")
    
    async def delete(self, symbol: str, country: str = "Saudi Arabia") -> int:
        """
        حذف بيانات الإحصائيات من الكاش
        """
        redis_key = self._get_cache_key(symbol, country)
        result = await redis_cache.delete(redis_key)
        print(f"🗑️ تم حذف {result} مفتاح من الكاش للرمز: {symbol}")
        return result
    
    async def clear_all_statistics(self) -> int:
        """مسح كل كاش الإحصائيات"""
        try:
            keys = await redis_cache.redis_client.keys(f"{self.cache_prefix}:*")
            if keys:
                await redis_cache.redis_client.delete(*keys)
            print(f"🧹 تم مسح {len(keys)} مفتاح من كاش الإحصائيات")
            return len(keys)
        except Exception as e:
            print(f"❌ خطأ في مسح كاش الإحصائيات: {e}")
            return 0

# إنشاء نسخة عامة
statistics_cache = StatisticsCache()