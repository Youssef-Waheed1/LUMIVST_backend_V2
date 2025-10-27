import httpx
from app.core.config import BASE_URL, API_KEY
import json

def clean_symbol(symbol: str) -> str:
    """Remove market suffix like .SA, .SABE, etc."""
    return symbol.split('.')[0]

async def get_income_statement(symbol: str, period: str = "annual", limit: int = 6):
    clean_sym = clean_symbol(symbol)
    url = f"{BASE_URL}/income_statement"
    params = {
        "symbol": clean_sym, 
        "exchange": "TADAWUL", 
        "period": period, 
        "apikey": API_KEY,
        "limit": limit
    }
    
    print(f"🔍 Fetching income statement for {symbol} -> {clean_sym} - {limit} years")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            print(f"📊 Income response for {clean_sym}: {len(data.get('income_statement', []))} years")
            
            # طباعة السنوات المتاحة
            if data.get('income_statement'):
                years = [item.get('fiscal_date') or item.get('year') for item in data['income_statement']]
                print(f"📅 سنوات الدخل المتاحة: {years}")
            
            return data
    except Exception as e:
        print(f"❌ Error fetching income statement for {symbol}: {e}")
        # إرجاع بيانات فارغة بدلاً من رمي خطأ
        return {"income_statement": []}

async def get_balance_sheet(symbol: str, period: str = "annual", limit: int = 6):
    clean_sym = clean_symbol(symbol)
    url = f"{BASE_URL}/balance_sheet"
    params = {
        "symbol": clean_sym, 
        "exchange": "TADAWUL", 
        "period": period, 
        "apikey": API_KEY,
        "limit": limit
    }
    
    print(f"🔍 Fetching balance sheet for {symbol} -> {clean_sym} - {limit} years")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            print(f"📊 Balance response for {clean_sym}: {len(data.get('balance_sheet', []))} years")
            
            # طباعة السنوات المتاحة
            if data.get('balance_sheet'):
                years = [item.get('fiscal_date') or item.get('year') for item in data['balance_sheet']]
                print(f"📅 سنوات الميزانية المتاحة: {years}")
            
            return data
    except Exception as e:
        print(f"❌ Error fetching balance sheet for {symbol}: {e}")
        # إرجاع بيانات فارغة بدلاً من رمي خطأ
        return {"balance_sheet": []}

async def get_cash_flow(symbol: str, period: str = "annual", limit: int = 6):
    clean_sym = clean_symbol(symbol)
    url = f"{BASE_URL}/cash_flow"
    params = {
        "symbol": clean_sym, 
        "exchange": "TADAWUL", 
        "period": period, 
        "apikey": API_KEY,
        "limit": limit
    }
    
    print(f"🔍 Fetching cash flow for {symbol} -> {clean_sym} - {limit} years")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            print(f"📊 Cash flow response for {clean_sym}: {len(data.get('cash_flow', []))} years")
            
            # طباعة السنوات المتاحة
            if data.get('cash_flow'):
                years = [item.get('fiscal_date') or item.get('year') for item in data['cash_flow']]
                print(f"📅 سنوات التدفقات المتاحة: {years}")
            
            return data
    except Exception as e:
        print(f"❌ Error fetching cash flow for {symbol}: {e}")
        # إرجاع بيانات فارغة بدلاً من رمي خطأ
        return {"cash_flow": []}