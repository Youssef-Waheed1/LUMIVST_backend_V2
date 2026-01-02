import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
from dateutil.relativedelta import relativedelta
from datetime import date

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_daily_rs(db_url: str, target_date=None):
    """
    Calculates RS Rating for a SPECIFIC DATE using the Calendar Months method.
    Optimized for incremental updates.
    """
    if target_date is None:
        target_date = date.today()
        
    logger.info(f"🚀 Starting RS Calculation V3 (Calendar Months) for date: {target_date}")
    
    engine = create_engine(db_url)
    
    # 1. Fetch Data: We need Price history for at least 1 year prior to target_date
    # plus the target_date itself.
    # To be safe and allow 12-month calculation, we fetch from (target_date - 13 months)
    start_date = pd.to_datetime(target_date) - pd.DateOffset(months=14)
    
    query = text("""
        SELECT symbol, date, close
        FROM prices
        WHERE date >= :start_date AND date <= :end_date
        ORDER BY symbol, date
    """)
    
    logger.info("📥 Fetching historical price data...")
    df = pd.read_sql(query, engine, params={'start_date': start_date, 'end_date': target_date})
    
    if df.empty:
        logger.warning(f"⚠️ No price data found for date {target_date} or prior period.")
        return

    # Ensure date is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter for the target date to identify active stocks
    active_symbols_df = df[df['date'].dt.date == target_date]
    if active_symbols_df.empty:
        logger.warning(f"⚠️ No prices found for TARGET DATE {target_date}. Run scraper first.")
        return

    active_symbols = active_symbols_df['symbol'].unique()
    logger.info(f"📊 Calculating RS for {len(active_symbols)} active stocks...")

    # 2. Optimized Return Calculation using merge_asof logic (Fastest)
    results = []
    
    # Pre-sort for merge_asof
    df = df.sort_values(['date']) 
    
    # We only care about active symbols
    df = df[df['symbol'].isin(active_symbols)]

    # Function to get returns lookback
    def get_returns_for_period(df_main, months):
        target_dates = df_main[['date', 'symbol', 'close']].copy()
        target_dates['lookback_date'] = target_dates['date'] - pd.DateOffset(months=months)
        
        # Sort for asof merge
        target_dates = target_dates.sort_values('lookback_date')
        lookup_df = df_main[['date', 'symbol', 'close']].sort_values('date').rename(columns={'date': 'past_date', 'close': 'past_close'})
        
        merged = pd.merge_asof(
            target_dates,
            lookup_df,
            left_on='lookback_date',
            right_on='past_date',
            by='symbol',
            direction='backward',
            tolerance=pd.Timedelta(days=7) # Allow looking back 7 days if exact date missing (weekend/holiday)
        )
        
        # Calculate Return
        # Return = (Current / Past) - 1
        merged[f'return_{months}m'] = (merged['close'] / merged['past_close']) - 1
        
        return merged[['symbol', 'date', f'return_{months}m']]

    # We only need to calculate for the target_date rows
    target_rows = df[df['date'].dt.date == target_date].copy()
    
    # Check if we have enough history for 12m?
    # Actually, merge_asof will return NaN if no past data, which is handled by our Dynamic Weighting logic.
    
    # Calculate returns for 3, 6, 9, 12 months
    r3 = get_returns_for_period(df, 3)
    r6 = get_returns_for_period(df, 6)
    r9 = get_returns_for_period(df, 9)
    r12 = get_returns_for_period(df, 12)
    
    # Merge all returns into one dataframe
    final_df = target_rows[['symbol', 'date', 'close']].copy()
    final_df = final_df.merge(r3[['symbol', f'return_3m']], on='symbol', how='left')
    final_df = final_df.merge(r6[['symbol', f'return_6m']], on='symbol', how='left')
    final_df = final_df.merge(r9[['symbol', f'return_9m']], on='symbol', how='left')
    final_df = final_df.merge(r12[['symbol', f'return_12m']], on='symbol', how='left')

    # 3. Calculate RS Raw (Dynamic Weighting)
    def calculate_weighted_rs(row):
        weights = {'return_3m': 0.4, 'return_6m': 0.2, 'return_9m': 0.2, 'return_12m': 0.2}
        valid_returns = {}
        total_weight = 0
        
        for col, weight in weights.items():
            if pd.notna(row.get(col)):
                valid_returns[col] = row[col]
                total_weight += weight
        
        # Relaxation: If we have at least 3M return, we can calculate something
        if not valid_returns:
            return None
            
        rs_raw = 0
        for col, val in valid_returns.items():
            normalized_weight = weights[col] / total_weight
            rs_raw += val * normalized_weight
            
        return rs_raw

    final_df['rs_raw'] = final_df.apply(calculate_weighted_rs, axis=1)

    # 4. Calculate Percentile Rank (RS Rating)
    # Filter out stocks with no rs_raw
    valid_rs = final_df.dropna(subset=['rs_raw'])
    
    if not valid_rs.empty:
        # 1-99 Rank
        final_df.loc[valid_rs.index, 'rs_rating'] = (
            valid_rs['rs_raw']
            .rank(pct=True)
            .mul(100)
            .round(0)
            .clip(upper=99) #, lower=1? usually 1-99
            .astype('Int64') # Int64 allows NaN
        )
        
        # Ensure minimum 1 if not 0? Standard IBD is 1-99.
        # If rank is 0 after rounding (lowest stock), set to 1?
        final_df.loc[final_df['rs_rating'] == 0, 'rs_rating'] = 1
        
    # Also calculate ranks for periods (for display)
    for p in [3, 6, 9, 12]:
        col = f'return_{p}m'
        valid = final_df.dropna(subset=[col])
        if not valid.empty:
             final_df.loc[valid.index, f'rank_{p}m'] = (
                valid[col].rank(pct=True).mul(100).round(0).clip(upper=99).astype('Int64')
             )

    # 5. Save to Database (Upsert Logic)
    logger.info("💾 Saving results to rs_daily table...")
    
    # Prepare data for insertion
    # Table rs_daily columns: symbol, date, rs_rating, rs_raw, rank_3m, rank_6m, rank_9m, rank_12m
    # We might need to map column names
    
    records = final_df.replace({np.nan: None}).to_dict(orient='records')
    
    # Direct SQL Upsert
    with engine.begin() as conn:
        for rec in records:
            stmt = text("""
                INSERT INTO rs_daily (symbol, date, rs_rating, rs_raw, 
                                      return_3m, return_6m, return_9m, return_12m)
                VALUES (:symbol, :date, :rs_rating, :rs_raw,
                        :rank_3m, :rank_6m, :rank_9m, :rank_12m)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    rs_rating = EXCLUDED.rs_rating,
                    rs_raw = EXCLUDED.rs_raw,
                    return_3m = EXCLUDED.return_3m,
                    return_6m = EXCLUDED.return_6m,
                    return_9m = EXCLUDED.return_9m,
                    return_12m = EXCLUDED.return_12m;
            """)
            
            # Note: In our previous schema we misused 'return_Xs' columns to store ranks based on frontend requirement.
            # I will continue this pattern: store RANKS in 'return_Xm' columns
            # But 'rs_raw' stores the raw weighted return.
            
            conn.execute(stmt, {
                'symbol': rec['symbol'],
                'date': target_date,
                'rs_rating': rec['rs_rating'],
                'rs_raw': rec['rs_raw'],
                'rank_3m': rec.get(f'rank_3m'),
                'rank_6m': rec.get(f'rank_6m'),
                'rank_9m': rec.get(f'rank_9m'),
                'rank_12m': rec.get(f'rank_12m')
            })
            
    logger.info(f"✅ Successfully updated RS for {len(records)} stocks on {target_date}.")

if __name__ == "__main__":
    # Test run
    REGION_DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"
    calculate_daily_rs(REGION_DB_URL)
