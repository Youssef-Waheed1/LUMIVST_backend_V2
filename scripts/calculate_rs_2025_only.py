import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
from pathlib import Path
from dateutil.relativedelta import relativedelta

# Setup
REGION_DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"
OUTPUT_FILE = Path(__file__).parent.parent / "rs_results_2025.csv"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_rs_for_2025_only():
    """
    حساب RS لسنة 2025 فقط للمقارنة مع WebScraping
    باستخدام Calendar Months (مش Trading Days) عشان نطابق موقع تداول
    """
    logger.info("🧪 Calculating RS for 2025 ONLY (Calendar Months Method)")
    
    engine = create_engine(REGION_DB_URL)
    
    with engine.connect() as conn:
        # جلب كل البيانات (نحتاج التاريخ الكامل لحساب الفترات)
        query = text("""
            SELECT date, symbol, close, company_name
            FROM prices 
            ORDER BY symbol, date
        """)
        df = pd.read_sql(query, conn)
    
    logger.info(f"📊 Loaded {len(df)} total records.")
    
    # تحويل التاريخ
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by=['symbol', 'date'])
    
    # ✅ حساب Returns باستخدام Trading Days (الطريقة الأسرع والأدق)
    logger.info("⚡ Calculating Returns using Trading Days...")
    
    def calc_return(series, period_days):
        return (series / series.shift(period_days)) - 1
    
    grouped = df.groupby('symbol')['close']
    df['return_3m'] = grouped.transform(lambda x: calc_return(x, 63))
    df['return_6m'] = grouped.transform(lambda x: calc_return(x, 126))
    df['return_9m'] = grouped.transform(lambda x: calc_return(x, 189))
    df['return_12m'] = grouped.transform(lambda x: calc_return(x, 252))
    
    logger.info("✅ Returns calculated successfully.")
    
    # ✅ حساب RS Raw (مع التعامل مع الفترات الناقصة)
    logger.info("⚡ Calculating RS Raw with Dynamic Weighting...")
    
    def calculate_weighted_rs(row):
        # الأوزان الأصلية
        weights = {
            'return_3m': 0.4,
            'return_6m': 0.2,
            'return_9m': 0.2,
            'return_12m': 0.2
        }
        
        valid_returns = {}
        total_weight = 0
        
        # تجميع الفترات المتاحة
        for col, weight in weights.items():
            val = row[col]
            if pd.notna(val):
                valid_returns[col] = val
                total_weight += weight
        
        # شرط: لازم يكون في بيانات لفترتين على الأقل (أحدهما 3 شهور يفضل)
        # للتساهل في التست، هنقبل لو فترة واحدة 3 شهور موجودة
        if not valid_returns:
            return None
            
        # إعادة توزيع الأوزان (Normalization)
        rs_raw = 0
        for col, val in valid_returns.items():
            # الوزن الجديد = الوزن الأصلي / مجموع الأوزان المتاحة
            normalized_weight = weights[col] / total_weight
            rs_raw += val * normalized_weight
            
        return rs_raw

    # تطبيق الدالة على كل صف
    df['rs_raw'] = df.apply(calculate_weighted_rs, axis=1)
    def get_rank(series):
        ranks = (series.rank(pct=True) * 100).round(0).clip(upper=99)
        return ranks.fillna(0).astype('Int64')
    
    logger.info("⚡ Calculating Ranks per period...")
    
    df['rank_3m'] = df.groupby('date')['return_3m'].transform(get_rank)
    df['rank_6m'] = df.groupby('date')['return_6m'].transform(get_rank)
    df['rank_9m'] = df.groupby('date')['return_9m'].transform(get_rank)
    df['rank_12m'] = df.groupby('date')['return_12m'].transform(get_rank)
    
    # ✅ حساب RS Final من rs_raw
    df['rs_rating'] = df.groupby('date')['rs_raw'].transform(get_rank)
    
    # تصفية لسنة 2025 فقط
    df_2025 = df[df['date'].dt.year == 2025].copy()
    
    # أخذ آخر يوم متاح في 2025
    latest_date = df_2025['date'].max()
    logger.info(f"📅 Latest date in 2025: {latest_date.date()}")
    
    final_results = df_2025[df_2025['date'] == latest_date].copy()
    
    # ترتيب حسب RS (الأعلى أولاً)
    final_results = final_results.sort_values('rs_rating', ascending=False)
    
    # اختيار الأعمدة المهمة
    output_cols = [
        'symbol', 'company_name', 'close',
        'rank_3m', 'rank_6m', 'rank_9m', 'rank_12m',
        'rs_rating'
    ]
    
    final_results = final_results[output_cols].copy()
    
    # إعادة تسمية الأعمدة للوضوح
    final_results.columns = [
        'Symbol', 'Company', 'Close',
        'RS_3Months', 'RS_6Months', 'RS_9Months', 'RS_1Year',
        'RS'
    ]
    
    # حفظ في CSV
    final_results.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    logger.info(f"💾 Saved results to: {OUTPUT_FILE}")
    
    # عرض عينة
    print("\n" + "="*100)
    print(f"📊 TOP 10 STOCKS BY RS (Date: {latest_date.date()})")
    print("="*100)
    print(final_results.head(10).to_string(index=False))
    
    print("\n" + "="*100)
    print("🔍 SAMPLE STOCKS FOR COMPARISON:")
    print("="*100)
    
    test_symbols = ['1120', '8260', '2030', '4191', '2382']  # الراجحي، الخليجية، سارك، أبو معطي، عديس
    for sym in test_symbols:
        stock = final_results[final_results['Symbol'] == sym]
        if not stock.empty:
            print(f"\n{stock.to_string(index=False)}")
    
    print("\n" + "="*100)
    print(f"✅ Total stocks processed: {len(final_results)}")
    print(f"📁 Full results saved to: {OUTPUT_FILE.name}")
    print("="*100 + "\n")
    
    return final_results

if __name__ == "__main__":
    calculate_rs_for_2025_only()
