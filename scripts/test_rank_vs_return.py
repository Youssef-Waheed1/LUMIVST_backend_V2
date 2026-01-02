import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging

# Setup
REGION_DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"
TEST_SYMBOLS = ["1120", "8260"]  # Al Rajhi & Gulf General

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_both_methods():
    """
    مقارنة طريقتين لحساب RS:
    1. Weighted Returns (الحالية)
    2. Weighted Ranks (المقترحة)
    """
    logger.info("🧪 Testing RS Calculation: Returns vs Ranks")
    
    engine = create_engine(REGION_DB_URL)
    
    with engine.connect() as conn:
        # جلب بيانات آخر سنة فقط (2024-2025)
        query = text("""
            SELECT date, symbol, close 
            FROM prices 
            WHERE date >= '2024-01-01'
            ORDER BY symbol, date
        """)
        df = pd.read_sql(query, conn)
    
    logger.info(f"📊 Loaded {len(df)} records from 2024-2025.")
    
    # تحويل التاريخ
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['symbol', 'date'])
    
    # حساب Returns
    grouped = df.groupby('symbol')['close']
    df['r3m'] = grouped.transform(lambda x: (x / x.shift(63)) - 1)
    df['r6m'] = grouped.transform(lambda x: (x / x.shift(126)) - 1)
    df['r9m'] = grouped.transform(lambda x: (x / x.shift(189)) - 1)
    df['r12m'] = grouped.transform(lambda x: (x / x.shift(252)) - 1)
    
    # طريقة 1: Weighted Returns (الحالية)
    df['score_returns'] = (
        0.4 * df['r3m'] + 
        0.2 * df['r6m'] + 
        0.2 * df['r9m'] + 
        0.2 * df['r12m']
    )
    
    # حساب Ranks لكل فترة
    def get_rank(series):
        ranks = (series.rank(pct=True) * 100).round(0)
        return ranks.fillna(0).astype('Int64')  # استخدام Int64 nullable
    
    df['rank_3m'] = df.groupby('date')['r3m'].transform(get_rank)
    df['rank_6m'] = df.groupby('date')['r6m'].transform(get_rank)
    df['rank_9m'] = df.groupby('date')['r9m'].transform(get_rank)
    df['rank_12m'] = df.groupby('date')['r12m'].transform(get_rank)
    
    # طريقة 2: Weighted Ranks (المقترحة)
    df['score_ranks'] = (
        0.4 * df['rank_3m'] + 
        0.2 * df['rank_6m'] + 
        0.2 * df['rank_9m'] + 
        0.2 * df['rank_12m']
    )
    
    # حساب RS Final لكل طريقة
    df['rs_from_returns'] = df.groupby('date')['score_returns'].transform(get_rank)
    df['rs_from_ranks'] = df.groupby('date')['score_ranks'].transform(get_rank)
    
    # عرض النتائج لآخر يوم متاح
    latest_date = df['date'].max()
    latest_data = df[df['date'] == latest_date].copy()
    
    print("\n" + "="*80)
    print(f"📅 COMPARISON FOR DATE: {latest_date.date()}")
    print("="*80)
    
    for symbol in TEST_SYMBOLS:
        stock = latest_data[latest_data['symbol'] == symbol]
        if stock.empty:
            print(f"\n⚠️ Symbol {symbol} not found.")
            continue
        
        s = stock.iloc[0]
        print(f"\n🏦 {symbol} ({s.get('company_name', 'N/A')})")
        print("-" * 40)
        print(f"💰 Close: {s['close']}")
        print("\n📈 RETURNS (%):")
        print(f"   3M: {s['r3m']*100:.2f}% → Rank: {s['rank_3m']}")
        print(f"   6M: {s['r6m']*100:.2f}% → Rank: {s['rank_6m']}")
        print(f"   9M: {s['r9m']*100:.2f}% → Rank: {s['rank_9m']}")
        print(f"   1Y: {s['r12m']*100:.2f}% → Rank: {s['rank_12m']}")
        print("\n🏆 FINAL RS RATING:")
        print(f"   Method 1 (Weighted Returns): {s['rs_from_returns']}")
        print(f"   Method 2 (Weighted Ranks):   {s['rs_from_ranks']}")
        print(f"   Difference: {abs(s['rs_from_returns'] - s['rs_from_ranks'])}")
    
    print("\n" + "="*80)
    print("💡 RECOMMENDATION:")
    print("   If 'Weighted Ranks' gives closer results to your reference,")
    print("   we should switch to that method permanently.")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_both_methods()
