import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalCalculator:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)

    def load_data(self):
        query = """
        SELECT id, symbol, date, close, volume_traded
        FROM prices
        ORDER BY symbol, date
        """
        logger.info("⏳ Loading price data...")
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        df['date'] = pd.to_datetime(df['date'])
        logger.info(f"✅ Loaded {len(df)} rows.")
        return df

    def calculate(self, df):
        logger.info("📈 Calculating Technical Indicators...")
        
        # Sort just in case
        df = df.sort_values(['symbol', 'date'])
        
        # Group by symbol
        grouped = df.groupby('symbol')

        # 1. SMAs
        logger.info("   ... SMAs (10, 21, 50, 150, 200)")
        df['sma_10'] = grouped['close'].transform(lambda x: x.rolling(window=10).mean())
        df['sma_21'] = grouped['close'].transform(lambda x: x.rolling(window=21).mean())
        df['sma_50'] = grouped['close'].transform(lambda x: x.rolling(window=50).mean())
        df['sma_150'] = grouped['close'].transform(lambda x: x.rolling(window=150).mean())
        df['sma_200'] = grouped['close'].transform(lambda x: x.rolling(window=200).mean())

        # 2. 52 Week High/Low (252 trading days)
        logger.info("   ... 52-Week High/Low")
        df['fifty_two_week_high'] = grouped['close'].transform(lambda x: x.rolling(window=252).max())
        df['fifty_two_week_low'] = grouped['close'].transform(lambda x: x.rolling(window=252).min())

        # 3. Average Volume (50 days)
        logger.info("   ... Avg Volume 50")
        df['average_volume_50'] = grouped['volume_traded'].transform(lambda x: x.rolling(window=50).mean())

        # 4. Differences (Price - SMA)
        logger.info("   ... Calculating Differences (Price - SMA)")
        df['price_minus_sma_10'] = df['close'] - df['sma_10']
        df['price_minus_sma_21'] = df['close'] - df['sma_21']
        df['price_minus_sma_50'] = df['close'] - df['sma_50']
        df['price_minus_sma_150'] = df['close'] - df['sma_150']
        df['price_minus_sma_200'] = df['close'] - df['sma_200']

        # 5. Percentage Differences
        logger.info("   ... Calculating Percentages")
        for window in [10, 21, 50, 150, 200]:
            col_sma = f'sma_{window}'
            col_target = f'price_vs_sma_{window}_percent'
            # Use .replace(0, np.nan) to avoid division by zero
            df[col_target] = ((df['close'] - df[col_sma]) / df[col_sma].replace(0, np.nan)) * 100
        
        # 52 Week High/Low Percent
        df['percent_off_52w_high'] = ((df['close'] - df['fifty_two_week_high'].replace(0, np.nan)) / df['fifty_two_week_high'].replace(0, np.nan)) * 100
        df['percent_off_52w_low'] = ((df['close'] - df['fifty_two_week_low'].replace(0, np.nan)) / df['fifty_two_week_low'].replace(0, np.nan)) * 100
        
        # Volume Diff Percent
        df['vol_diff_50_percent'] = ((df['volume_traded'] - df['average_volume_50']) / df['average_volume_50'].replace(0, np.nan)) * 100

        # Replace inf and -inf with NaN
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Replace NaNs with None for SQL
        cols_to_update = [
            'price_minus_sma_10', 'price_minus_sma_21', 'price_minus_sma_50', 
            'price_minus_sma_150', 'price_minus_sma_200',
            'fifty_two_week_high', 'fifty_two_week_low', 'average_volume_50',
            'price_vs_sma_10_percent', 'price_vs_sma_21_percent', 'price_vs_sma_50_percent',
            'price_vs_sma_150_percent', 'price_vs_sma_200_percent',
            'percent_off_52w_high', 'percent_off_52w_low', 'vol_diff_50_percent'
        ]
        
        # Rounding
        for col in cols_to_update:
             if 'volume' not in col:
                 df[col] = df[col].round(2)
             elif col == 'average_volume_50':
                 df[col] = df[col].fillna(0).astype(int)

        # Filter rows where at least one calculation is valid (though for update we might want to update all?)
        # Let's keep all rows that have at least some data.
        # However, saving 1M rows purely for updates is slow via ORM.
        # We will use temporary table approach or efficient update.
        # Given "Render" limitations, let's update only Today's data?
        # User wants "Add columns". If we only update today, history remains empty.
        # But maybe that's fine? The frontend table usually shows LATEST data.
        # User didn't ask for charts of these indicators yet.
        # Let's start by Filtering for the LATEST date per symbol to speed up SAVING for the Table.
        # But wait, if I want to show "52 week high", I need it for today.
        
        return df

    def save_latest(self, df):
        """
        Updates only the LATEST record for each symbol.
        """
        logger.info("💾 Preparing to save Latest Data...")
        
        # Get latest date per symbol
        latest_dates = df.groupby('symbol')['date'].max().reset_index()
        
        # Merge to get the full rows for latest dates
        latest_data = pd.merge(df, latest_dates, on=['symbol', 'date'])
        
        logger.info(f"   Updating {len(latest_data)} records (Latest only)...")
        
        # Create a temp table logic or execute_values
        # Using simple iteration for 300 rows is fast enough.
        
        conn = self.engine.connect()
        trans = conn.begin()
        
        try:
            for idx, row in latest_data.iterrows():
                update_stmt = text("""
                    UPDATE prices
                    SET price_minus_sma_10 = :p10,
                        price_minus_sma_21 = :p21,
                        price_minus_sma_50 = :p50,
                        price_minus_sma_150 = :p150,
                        price_minus_sma_200 = :p200,
                        fifty_two_week_high = :h52,
                        fifty_two_week_low = :l52,
                        average_volume_50 = :avg_vol,
                        
                        price_vs_sma_10_percent = :p10_pct,
                        price_vs_sma_21_percent = :p21_pct,
                        price_vs_sma_50_percent = :p50_pct,
                        price_vs_sma_150_percent = :p150_pct,
                        price_vs_sma_200_percent = :p200_pct,
                        percent_off_52w_high = :pct_off_high,
                        percent_off_52w_low = :pct_off_low,
                        vol_diff_50_percent = :vol_diff_pct
                    WHERE id = :id
                """)
                
                params = {
                    'p10': row['price_minus_sma_10'] if pd.notnull(row['price_minus_sma_10']) else None,
                    'p21': row['price_minus_sma_21'] if pd.notnull(row['price_minus_sma_21']) else None,
                    'p50': row['price_minus_sma_50'] if pd.notnull(row['price_minus_sma_50']) else None,
                    'p150': row['price_minus_sma_150'] if pd.notnull(row['price_minus_sma_150']) else None,
                    'p200': row['price_minus_sma_200'] if pd.notnull(row['price_minus_sma_200']) else None,
                    'h52': row['fifty_two_week_high'] if pd.notnull(row['fifty_two_week_high']) else None,
                    'l52': row['fifty_two_week_low'] if pd.notnull(row['fifty_two_week_low']) else None,
                    'avg_vol': row['average_volume_50'] if pd.notnull(row['average_volume_50']) else None,
                    
                    'p10_pct': row['price_vs_sma_10_percent'] if pd.notnull(row['price_vs_sma_10_percent']) else None,
                    'p21_pct': row['price_vs_sma_21_percent'] if pd.notnull(row['price_vs_sma_21_percent']) else None,
                    'p50_pct': row['price_vs_sma_50_percent'] if pd.notnull(row['price_vs_sma_50_percent']) else None,
                    'p150_pct': row['price_vs_sma_150_percent'] if pd.notnull(row['price_vs_sma_150_percent']) else None,
                    'p200_pct': row['price_vs_sma_200_percent'] if pd.notnull(row['price_vs_sma_200_percent']) else None,
                    'pct_off_high': row['percent_off_52w_high'] if pd.notnull(row['percent_off_52w_high']) else None,
                    'pct_off_low': row['percent_off_52w_low'] if pd.notnull(row['percent_off_52w_low']) else None,
                    'vol_diff_pct': row['vol_diff_50_percent'] if pd.notnull(row['vol_diff_50_percent']) else None,
                    
                    'id': row['id']
                }
                
                conn.execute(update_stmt, params)
                
            trans.commit()
            logger.info("✅ Latest data updated successfully.")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"❌ Error updating db: {e}")
            raise
        finally:
            conn.close()

if __name__ == "__main__":
    calc = TechnicalCalculator(str(settings.DATABASE_URL))
    df = calc.load_data()
    df_calc = calc.calculate(df)
    calc.save_latest(df_calc)
