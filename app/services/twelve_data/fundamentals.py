import httpx
from app.core.config import settings
import json

def clean_symbol(symbol: str) -> str:
    """Remove market suffix like .SA, .SABE, etc."""
    return symbol.split('.')[0]

def get_exchange_by_country(country: str) -> str:
    """الحصول على رمز البورصة بناءً على البلد"""
    exchanges = {
        "Saudi Arabia": "TADAWUL",
        "UAE": "DFM",  # سوق دبي المالي
        "Egypt": "EGX",  # البورصة المصرية
        "Qatar": "QE",  # بورصة قطر
        "Kuwait": "BKP",  # بورصة الكويت
        "Oman": "MSM",  # سوق مسقط للأوراق المالية
        "Bahrain": "BSE"  # بورصة البحرين
    }
    return exchanges.get(country, "TADAWUL")  # افتراضي السعودية

async def get_income_statement(symbol: str, country: str = "Saudi Arabia", period: str = "annual", limit: int = 6):
    clean_sym = clean_symbol(symbol)
    exchange = get_exchange_by_country(country)
    
    url = f"{settings.BASE_URL}/income_statement"
    params = {
        "symbol": clean_sym, 
        "exchange": exchange, 
        "period": period, 
        "apikey": settings.API_KEY,
        "limit": limit
    }
    
    print(f"🔍 جلب قائمة الدخل: {symbol} -> {clean_sym} - البلد: {country} - البورصة: {exchange}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            print(f"📊 استجابة الدخل لـ {clean_sym}: {len(data.get('income_statement', []))} سنة")
            
            if data.get('income_statement'):
                years = [item.get('fiscal_date') or item.get('year') for item in data['income_statement']]
                print(f"📅 سنوات الدخل المتاحة لـ {clean_sym}: {years}")
            else:
                print(f"⚠️ لا توجد بيانات دخل لـ {clean_sym} في {country}")
            
            return data
    except Exception as e:
        print(f"❌ خطأ في جلب قائمة الدخل لـ {symbol}: {e}")
        return {"income_statement": []}

async def get_balance_sheet(symbol: str, country: str = "Saudi Arabia", period: str = "annual", limit: int = 6):
    clean_sym = clean_symbol(symbol)
    exchange = get_exchange_by_country(country)
    
    url = f"{settings.BASE_URL}/balance_sheet"
    params = {
        "symbol": clean_sym, 
        "exchange": exchange, 
        "period": period, 
        "apikey": settings.API_KEY,
        "limit": limit
    }
    
    print(f"🔍 جلب الميزانية العمومية: {symbol} -> {clean_sym} - البلد: {country} - البورصة: {exchange}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            print(f"📊 استجابة الميزانية لـ {clean_sym}: {len(data.get('balance_sheet', []))} سنة")
            
            if data.get('balance_sheet'):
                years = [item.get('fiscal_date') or item.get('year') for item in data['balance_sheet']]
                print(f"📅 سنوات الميزانية المتاحة لـ {clean_sym}: {years}")
            else:
                print(f"⚠️ لا توجد بيانات ميزانية لـ {clean_sym} في {country}")
            
            return data
    except Exception as e:
        print(f"❌ خطأ في جلب الميزانية العمومية لـ {symbol}: {e}")
        return {"balance_sheet": []}

async def get_cash_flow(symbol: str, country: str = "Saudi Arabia", period: str = "annual", limit: int = 6):
    clean_sym = clean_symbol(symbol)
    exchange = get_exchange_by_country(country)
    
    url = f"{settings.BASE_URL}/cash_flow"
    params = {
        "symbol": clean_sym, 
        "exchange": exchange, 
        "period": period, 
        "apikey": settings.API_KEY,
        "limit": limit
    }
    
    print(f"🔍 جلب التدفقات النقدية: {symbol} -> {clean_sym} - البلد: {country} - البورصة: {exchange}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            print(f"📊 استجابة التدفقات لـ {clean_sym}: {len(data.get('cash_flow', []))} سنة")
            
            if data.get('cash_flow'):
                years = [item.get('fiscal_date') or item.get('year') for item in data['cash_flow']]
                print(f"📅 سنوات التدفقات المتاحة لـ {clean_sym}: {years}")
            else:
                print(f"⚠️ لا توجد بيانات تدفقات نقدية لـ {clean_sym} في {country}")
            
            return data
    except Exception as e:
        print(f"❌ خطأ في جلب التدفقات النقدية لـ {symbol}: {e}")
        return {"cash_flow": []}