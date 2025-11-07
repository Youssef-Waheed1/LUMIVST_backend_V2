from fastapi import APIRouter, HTTPException, Query
from app.services.twelve_data.quote_service import get_stock_quote, get_multiple_quotes
from app.schemas.quote import StockQuoteResponse

router = APIRouter(prefix="/quote", tags=["Stock Quotes"])

@router.get("/{symbol}", response_model=StockQuoteResponse)
async def get_stock_quote_endpoint(
    symbol: str,
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")  # ⭐ جديد
):
    """جلب بيانات السعر لسهم معين"""
    try:
        quote_data = await get_stock_quote(symbol, country)  # ⭐ تم التعديل
        
        if not quote_data:
            raise HTTPException(status_code=404, detail=f"Stock quote for '{symbol}' not found")
        
        return quote_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات السعر: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=list[StockQuoteResponse])
async def get_multiple_quotes_endpoint(
    symbols: str = Query(..., description="رموز الأسهم مفصولة بفواصل"),
    country: str = Query("Saudi Arabia", description="البلد (افتراضي: Saudi Arabia)")  # ⭐ جديد
):
    """جلب بيانات الأسعار لعدة أسهم"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        
        if len(symbol_list) > 50:
            raise HTTPException(status_code=400, detail="Maximum 50 symbols allowed")
        
        quotes = await get_multiple_quotes(symbol_list, country)  # ⭐ تم التعديل
        
        return quotes
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات الأسعار: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")