from fastapi import APIRouter, HTTPException, Query
from app.services.cache.financial_cache import financial_cache
import json

router = APIRouter(prefix="/financials", tags=["Financials"])

@router.get("/income_statement/{symbol}")
async def income_statement(
    symbol: str,
    period: str = Query("annual", regex="^(annual|quarterly)$", description="Period: annual or quarterly"),
    limit: int = Query(6, ge=1, le=20, description="Number of periods to fetch (1-20)")
):
    try:
        print(f"📈 Income statement request with cache for: {symbol}")
        data = await financial_cache.get_income_statement(symbol, period=period, limit=limit)
        
        # تأكد من أن البيانات في التنسيق الصحيح
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {"income_statement": []}
        
        if not data.get('income_statement'):
            print(f"⚠️ No income data found for {symbol}")
            data = {"income_statement": []}
            
        return data
    except Exception as e:
        print(f"❌ Error in income statement for {symbol}: {e}")
        # إرجاع بيانات فارغة بدلاً من رمي خطأ
        return {"income_statement": []}

@router.get("/balance_sheet/{symbol}")
async def balance_sheet(
    symbol: str,
    period: str = Query("annual", regex="^(annual|quarterly)$", description="Period: annual or quarterly"),
    limit: int = Query(6, ge=1, le=20, description="Number of periods to fetch (1-20)")
):
    try:
        print(f"📊 Balance sheet request with cache for: {symbol}")
        data = await financial_cache.get_balance_sheet(symbol, period=period, limit=limit)
        
        # تأكد من أن البيانات في التنسيق الصحيح
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {"balance_sheet": []}
        
        if not data.get('balance_sheet'):
            print(f"⚠️ No balance sheet data found for {symbol}")
            data = {"balance_sheet": []}
            
        return data
    except Exception as e:
        print(f"❌ Error in balance sheet for {symbol}: {e}")
        return {"balance_sheet": []}

@router.get("/cash_flow/{symbol}")
async def cash_flow(
    symbol: str,
    period: str = Query("annual", regex="^(annual|quarterly)$", description="Period: annual or quarterly"),
    limit: int = Query(6, ge=1, le=20, description="Number of periods to fetch (1-20)")
):
    try:
        print(f"💰 Cash flow request with cache for: {symbol}")
        data = await financial_cache.get_cash_flow(symbol, period=period, limit=limit)
        
        # تأكد من أن البيانات في التنسيق الصحيح
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = {"cash_flow": []}
        
        if not data.get('cash_flow'):
            print(f"⚠️ No cash flow data found for {symbol}")
            data = {"cash_flow": []}
            
        return data
    except Exception as e:
        print(f"❌ Error in cash flow for {symbol}: {e}")
        return {"cash_flow": []}