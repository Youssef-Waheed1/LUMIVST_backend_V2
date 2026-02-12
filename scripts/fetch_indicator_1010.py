import sys, json, decimal
sys.path.insert(0, '.')
from app.core.database import SessionLocal
from app.models.stock_indicators import StockIndicator

def dec(v):
    if v is None:
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    return v

if __name__ == '__main__':
    db = SessionLocal()
    try:
        ind = db.query(StockIndicator).filter(StockIndicator.symbol == '1010').order_by(StockIndicator.date.desc()).first()
        if not ind:
            print('No indicator found for 1010')
            sys.exit(0)
        out = {
            'symbol': ind.symbol,
            'company_name': ind.company_name,
            'date': str(ind.date) if ind.date else None,
            'close': dec(ind.close),
            'sma4': dec(ind.sma4),
            'sma9': dec(ind.sma9),
            'sma18': dec(ind.sma18),
            'sma4_w': dec(ind.sma4_w),
            'sma9_w': dec(ind.sma9_w),
            'sma18_w': dec(ind.sma18_w),
            'price_gt_sma18': bool(ind.price_gt_sma18),
            'sma_trend_daily': bool(ind.sma_trend_daily),
            'sma_trend_weekly': bool(ind.sma_trend_weekly),
            'final_signal': bool(ind.final_signal),
            'score': int(ind.score) if ind.score is not None else None,
            'cfg_daily': dec(ind.cfg_daily),
            'cfg_ema45': dec(ind.cfg_ema45),
            'cci': dec(ind.cci),
            'cci_ema20': dec(ind.cci_ema20),
            'aroon_up': dec(ind.aroon_up),
            'aroon_down': dec(ind.aroon_down),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        db.close()
