import aiohttp
import asyncio
from typing import Optional, Dict, Any, List
from app.core.config import settings

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
    "2360", "2370", "2380", "2381", "2382", "3001", "3002", "3003", "3004", 
    "3005", "3007", "3008", "3010", "3020", "3030", "3040", "3050", "3060",
    "3080", "3090", "3091", "3092", "4001", "4002", "4003", "4004", "4005"
}

class StatisticsService:
    def __init__(self):
        self.base_url = "https://api.twelvedata.com"
        self.api_key = settings.TWELVE_DATA_API_KEY
        self.supported_symbols = SAUDI_STOCKS
        
    def _clean_symbol(self, symbol: str) -> str:
        """تنظيف الرمز من اللواحق مثل .SA"""
        if not symbol:
            return ""
        return ''.join(filter(str.isdigit, symbol)).upper()
        
    def _get_exchange_by_country(self, country: str) -> str:
        """الحصول على رمز البورصة بناءً على البلد"""
        exchanges = {
            "Saudi Arabia": "TADAWUL",
            "UAE": "DFM",
            "Egypt": "EGX", 
            "Qatar": "QE",
            "Kuwait": "BKP",
            "Oman": "MSM",
            "Bahrain": "BSE"
        }
        return exchanges.get(country, "TADAWUL")
    
    def is_symbol_supported(self, symbol: str) -> bool:
        """التحقق إذا كان الرمز مدعوم"""
        clean_sym = self._clean_symbol(symbol)
        return clean_sym in self.supported_symbols
        
    async def get_statistics(
        self,
        symbol: str,
        country: str = "Saudi Arabia"
    ) -> Dict[str, Any]:
        """
        جلب إحصائيات الشركة من Twelve Data API
        Cost: 50 credits per symbol
        """
        clean_symbol_val = self._clean_symbol(symbol)
        
        # التحقق من دعم الرمز
        if not self.is_symbol_supported(symbol):
            return {
                "error": "رمز غير مدعوم",
                "message": f"الرمز {symbol} غير موجود في قائمة الأسهم السعودية المدعومة",
                "supported_symbols_count": len(self.supported_symbols),
                "clean_symbol": clean_symbol_val
            }
        
        exchange = self._get_exchange_by_country(country)
        
        params = {
            "symbol": clean_symbol_val,
            "exchange": exchange,
            "country": country,
            "apikey": self.api_key
        }
        
        url = f"{self.base_url}/statistics"
        
        print(f"🌐 طلب إحصائيات: {symbol} -> {clean_symbol_val} - البلد: {country} - البورصة: {exchange}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # إضافة معلومات إضافية
                        data["_metadata"] = {
                            "symbol": symbol,
                            "clean_symbol": clean_symbol_val,
                            "country": country,
                            "exchange": exchange,
                            "is_supported": True,
                            "request_timestamp": asyncio.get_event_loop().time()
                        }
                        
                        # طباعة معلومات الاستجابة للت debugging
                        if data.get('meta'):
                            print(f"✅ تم جلب إحصائيات {clean_symbol_val}: {data['meta'].get('name', 'N/A')}")
                        else:
                            print(f"⚠️ لا توجد بيانات إحصائيات لـ {clean_symbol_val}")
                            
                        return data
                    else:
                        error_text = await response.text()
                        print(f"❌ خطأ API لـ {clean_symbol_val}: {response.status} - {error_text}")
                        return {
                            "error": f"API request failed: {response.status}",
                            "symbol": symbol,
                            "clean_symbol": clean_symbol_val,
                            "country": country
                        }
                        
        except aiohttp.ClientError as e:
            print(f"❌ خطأ شبكة لـ {clean_symbol_val}: {str(e)}")
            return {
                "error": f"Network error: {str(e)}",
                "symbol": symbol,
                "clean_symbol": clean_symbol_val
            }
        except asyncio.TimeoutError:
            print(f"❌ timeout لـ {clean_symbol_val}")
            return {
                "error": "Request timeout",
                "symbol": symbol,
                "clean_symbol": clean_symbol_val
            }
        except Exception as e:
            print(f"❌ خطأ غير متوقع لـ {clean_symbol_val}: {str(e)}")
            return {
                "error": f"Unexpected error: {str(e)}",
                "symbol": symbol,
                "clean_symbol": clean_symbol_val
            }
    
    async def get_bulk_statistics(
        self,
        symbols: List[str],
        country: str = "Saudi Arabia"
    ) -> Dict[str, Any]:
        """
        جلب إحصائيات مجموعة من الرموز
        """
        # تصفية الرموز المدعومة فقط
        supported_symbols = [sym for sym in symbols if self.is_symbol_supported(sym)]
        unsupported_symbols = [sym for sym in symbols if not self.is_symbol_supported(sym)]
        
        print(f"📊 جلب إحصائيات {len(supported_symbols)} رمز مدعوم من أصل {len(symbols)}")
        
        if unsupported_symbols:
            print(f"⚠️ الرموز غير المدعومة: {unsupported_symbols}")
        
        if not supported_symbols:
            return {
                "data": [],
                "supported_symbols": supported_symbols,
                "unsupported_symbols": unsupported_symbols,
                "total_requested": len(symbols),
                "total_supported": len(supported_symbols),
                "message": "لا توجد رموز مدعومة في الطلب"
            }
        
        # جلب البيانات لكل رمز مدعوم
        tasks = [self.get_statistics(symbol, country) for symbol in supported_symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # معالجة النتائج
        successful_results = []
        failed_results = []
        
        for i, result in enumerate(results):
            symbol = supported_symbols[i]
            if isinstance(result, Exception):
                failed_results.append({
                    "symbol": symbol,
                    "error": str(result)
                })
            elif result.get("error"):
                failed_results.append({
                    "symbol": symbol,
                    "error": result.get("error")
                })
            else:
                successful_results.append(result)
        
        return {
            "data": successful_results,
            "failed_requests": failed_results,
            "supported_symbols": supported_symbols,
            "unsupported_symbols": unsupported_symbols,
            "total_requested": len(symbols),
            "total_successful": len(successful_results),
            "total_failed": len(failed_results),
            "total_supported": len(supported_symbols),
            "country": country,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    def get_supported_symbols(self) -> List[str]:
        """الحصول على قائمة الرموز المدعومة"""
        return list(self.supported_symbols)