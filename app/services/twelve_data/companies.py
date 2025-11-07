import httpx
import math
from typing import Dict, List, Any
from app.core.config import API_KEY
import asyncio
from datetime import datetime

def clean_company_symbol(symbol: str) -> str:
    """تنظيف رمز الشركة للإنتاج"""
    if not symbol:
        return ""
    
    # نأخذ الأرقام فقط من الرمز
    clean_symbol = ''.join(filter(str.isdigit, symbol))
    return clean_symbol.upper() if clean_symbol else symbol.upper()



async def get_all_saudi_symbols(country: str = "Saudi Arabia") -> List[str]:  # ⭐ تم التعديل
    """جلب كل الرموز السعودية من TwelveData API"""
    try:
        url = "https://api.twelvedata.com/stocks"
        params = {
            "country": country,  # ⭐ تم التعديل
            "apikey": API_KEY
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            data = response.json()

        if "data" not in data:
            print("❌ لا توجد بيانات للأسهم السعودية")
            return []

        symbols = []
        for stock in data["data"]:
            symbol = stock.get("symbol", "")
            exchange = stock.get("exchange", "")
            
            # نأخذ فقط الأسهم في Tadawul
            if exchange == "Tadawul" and symbol:
                clean_symbol = clean_company_symbol(symbol)
                if clean_symbol and clean_symbol not in symbols:
                    symbols.append(clean_symbol)
        
        print(f"✅ تم جلب {len(symbols)} رمز سعودي من Tadawul")
        return symbols
        
    except Exception as e:
        print(f"❌ خطأ في جلب الرموز السعودية: {str(e)}")
        return []

async def get_stock_quote(symbol: str, country: str = "Saudi Arabia") -> Dict[str, Any]:  # ⭐ تم التعديل
    """جلب بيانات السهم من TwelveData API للإنتاج"""
    try:
        clean_symbol = clean_company_symbol(symbol)
        
        url = "https://api.twelvedata.com/quote"
        params = {
            "symbol": clean_symbol,
            "country": country,  # ⭐ جديد
            "apikey": API_KEY
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            data = response.json()

        # التحقق من وجود بيانات صالحة وأن السوق هو Tadawul
        if "code" in data or data.get("close") is None:
            return None
            
        # تصفية فقط الأسهم في سوق Tadawul
        if data.get("exchange") != "Tadawul":
            return None

        return data
        
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات السهم {symbol}: {str(e)}")
        return None

def _calculate_turnover(volume: str, close_price: str) -> str:
    """حساب قيمة التداول (Turnover)"""
    try:
        if volume and close_price and volume != "N/A" and close_price != "N/A":
            volume_num = float(str(volume).replace(',', ''))
            close_num = float(str(close_price).replace(',', ''))
            turnover = volume_num * close_num
            return f"{turnover:,.0f}"
        return "N/A"
    except (ValueError, TypeError):
        return "N/A"

async def get_tadawul_stocks_data(symbols: List[str], country: str = "Saudi Arabia") -> List[Dict[str, Any]]:  # ⭐ تم التعديل
    """جلب بيانات الأسهم السعودية في Tadawul فقط"""
    # تقسيم الرموز إلى مجموعات علشان ما نتعداش rate limit
    BATCH_SIZE = 10
    all_companies = []
    
    for i in range(0, len(symbols), BATCH_SIZE):
        batch_symbols = symbols[i:i + BATCH_SIZE]
        
        tasks = [get_stock_quote(symbol, country) for symbol in batch_symbols]  # ⭐ تم التعديل
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, result in enumerate(results):
            if isinstance(result, Exception):
                continue
                
            symbol = batch_symbols[j]
            
            if result is None:
                continue
                
            # التأكد مرة أخرى أن السوق هو Tadawul
            if result.get("exchange") == "Tadawul":
                company = {
                    "symbol": symbol,
                    "name": result.get("name", "N/A"),
                    "exchange": "Tadawul",
                    "mic_code": result.get("mic_code", "N/A"),
                    "currency": result.get("currency", "N/A"),
                    # البيانات المالية
                    "fifty_two_week_range": result.get("fifty_two_week", {}).get("range", "N/A"),
                    "price": result.get("close", "N/A"),
                    "change": result.get("change", "N/A"),
                    "change_percent": result.get("percent_change", "N/A"),
                    "previous_close": result.get("previous_close", "N/A"),
                    "volume": result.get("volume", "N/A"),
                    "turnover": _calculate_turnover(result.get("volume"), result.get("close")),
                    # بيانات توقيت
                    "last_updated": datetime.now().isoformat(),
                    "country": country  # ⭐ جديد
                }
                all_companies.append(company)
        
        # delay بين الـ batches علشان ما نتعداش rate limit
        if i + BATCH_SIZE < len(symbols):
            await asyncio.sleep(1)
    
    print(f"✅ تم جلب بيانات {len(all_companies)} سهم من Tadawul")
    return all_companies

async def get_all_companies_data(country: str = "Saudi Arabia") -> Dict[str, Any]:  # ⭐ تم التعديل
    """جلب كل بيانات الأسهم مرة واحدة"""
    try:
        print(f"📊 جلب كل بيانات أسهم Tadawul مرة واحدة")
        
        # جلب كل الرموز السعودية أولاً
        all_symbols = await get_all_saudi_symbols(country)  # ⭐ تم التعديل
        
        if not all_symbols:
            # Fallback: استخدم قائمة static إذا فشل جلب الرموز
            all_symbols = [
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
                        # "4006", "4007", "4008", "4009", "4010", "4011", "4012", "4013", "4014", 
                        # "4015", "4016", "4017", "4018", "4019", "4020", "4030", "4031", "4040", 
                        # "4050", "4061", "4070", "4071", "4072", "4080", "4081", "4082", "4083", 
                        # "4084", "4090", "4100", "4110", "4130", "4140", "4141", "4142", "4143", 
                        # "4144", "4145", "4146", "4150", "4160", "4161", "4162", "4163", "4164", 
                        # "4165", "4170", "4180", "4190", "4191", "4192", "4193", "4194", "4200", 
                        # "4210", "4220", "4230", "4240", "4250", "4260", "4261", "4262", "4263", 
                        # "4264", "4270", "4280", "4290", "4291", "4292", "4300", "4310", "4320", 
                        # "4321", "4322", "4323", "4324", "4325", "4326", "4330", "4331", "4332", 
                        # "4333", "4334", "4335", "4336", "4337", "4338", "4339", "4340", "4342", 
                        # "4344", "4345", "4346", "4347", "4348", "4349", "4350", "5110", "6010", 
                        # "6012", "6013", "6014", "6015", "6016", "6017", "6018", "6020", "6040", 
                        # "6050", "6060", "6070", "6090", "7001", "7010", "7020", "7030", "7200", 
                        # "7201", "7202", "7203", "7204", "7211", "8010", "8012", "8020", "8030", 
                        # "8040", "8050", "8060", "8070", "8100", "8120", "8150", "8160", "8170", 
                        # "8180", "8190", "8200", "8210", "8230", "8240", "8250", "8260", "8280", 
                        # "8300", "8310", "8311", "8313", "9644", "9645", "9648", "9649"
            ]
            print(f"⚠️ استخدام القائمة الاحتياطية بها {len(all_symbols)} رمز")
        
        # جلب البيانات لكل الرموز
        companies_data = await get_tadawul_stocks_data(all_symbols, country)  # ⭐ تم التعديل
        
        print(f"✅ تم جلب بيانات {len(companies_data)} سهم من أصل {len(all_symbols)}")
        
        return {
            "data": companies_data,
            "total": len(companies_data),
            "timestamp": datetime.now().isoformat(),
            "country": country  # ⭐ جديد
        }
        
    except Exception as e:
        print(f"❌ خطأ في get_all_companies_data: {str(e)}")
        return {"data": [], "total": 0}

def convert_api_data_to_company_model(api_data: Dict[str, Any]) -> Dict[str, Any]:
    """تحويل بيانات API إلى نموذج Company"""
    return {
        "symbol": api_data.get("symbol", ""),
        "name": api_data.get("name", "N/A"),
        "currency": api_data.get("currency", "N/A"),
        "exchange": api_data.get("exchange", "Tadawul"),
        "mic_code": api_data.get("mic_code", "N/A"),
        "country": api_data.get("country", "Saudi Arabia"),  # ⭐ تم التعديل
        "type": "Stock",
        "price": float(api_data.get("price", 0)) if api_data.get("price") and api_data.get("price") != "N/A" else None,
        "change": float(api_data.get("change", 0)) if api_data.get("change") and api_data.get("change") != "N/A" else None,
        "change_percent": float(api_data.get("change_percent", 0)) if api_data.get("change_percent") and api_data.get("change_percent") != "N/A" else None,
        "previous_close": float(api_data.get("previous_close", 0)) if api_data.get("previous_close") and api_data.get("previous_close") != "N/A" else None,
        "volume": int(api_data.get("volume", 0)) if api_data.get("volume") and api_data.get("volume") != "N/A" else None,
        "turnover": api_data.get("turnover", "N/A"),
        "fifty_two_week_range": api_data.get("fifty_two_week_range", "N/A"),
        "fifty_two_week_low": float(api_data.get("fifty_two_week_low", 0)) if api_data.get("fifty_two_week_low") and api_data.get("fifty_two_week_low") != "N/A" else None,
        "fifty_two_week_high": float(api_data.get("fifty_two_week_high", 0)) if api_data.get("fifty_two_week_high") and api_data.get("fifty_two_week_high") != "N/A" else None,
    }