
import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import logging
from datetime import date, timedelta, datetime
from sqlalchemy import text, func, desc
from sqlalchemy.orm import Session

# Setup Paths
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models.industry_group import IndustryGroupHistory
from app.models.price import Price
from app.models.financials import IncomeStatement

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndustryGroupCalculator:
    def __init__(self, db: Session):
        self.db = db

    def load_metric_data(self, target_date: date):
        """
        Loads necessary data: 
        1. Prices at target_date
        2. Prices at start of year (for YTD)
        3. Latest Shares Outstanding (for Market Cap)
        """
        logger.info(f"📡 Loading Data for {target_date}...")
        
        # 1. Get Latest Prices for Target Date
        # optimization: use distinct on symbol order by date desc limit 1 per symbol <= target_date
        # simpler: just filter date = target_date. If weekend, user handles it by passing correct date?
        # Let's try to get "latest available price up to target_date" per symbol to catch non-traded stocks
        
        # Using pandas for ease of aggregation
        query_prices = text("""
            SELECT DISTINCT ON (symbol) symbol, date, close, industry_group, sector, market_cap
            FROM prices
            WHERE date <= :target_date
            ORDER BY symbol, date DESC
        """)
        
        with self.db.bind.connect() as connection:
            df_prices = pd.read_sql(query_prices, connection, params={"target_date": target_date})
            
        logger.info(f"   Loaded current prices for {len(df_prices)} symbols")
        
        # 2. Get Start of Year Prices (for YTD)
        start_of_year = date(target_date.year, 1, 1)
        # Find first trading day of year per symbol
        # Query: Get first record >= Jan 1
        query_ytd = text("""
            SELECT DISTINCT ON (symbol) symbol, close as close_ytd_start
            FROM prices
            WHERE date >= :start_of_year AND date <= :target_date
            ORDER BY symbol, date ASC
        """)
        
        with self.db.bind.connect() as connection:
            df_ytd = pd.read_sql(query_ytd, connection, params={"start_of_year": start_of_year, "target_date": target_date})
            
        logger.info(f"   Loaded YTD start prices for {len(df_ytd)} symbols")

        # Merge All
        df = pd.merge(df_prices, df_ytd, on='symbol', how='left')
        
        return df

    def calculate_metrics(self, df: pd.DataFrame):
        """
        Calculate metrics per stock then aggregate
        """
        # Calculate Market Cap (Convert to Billions)
        # Handle missing market caps
        df['market_cap'] = df['market_cap'].fillna(0.0)
        df['market_cap_bil'] = df['market_cap'] / 1_000_000_000.0
        
        # Calculate YTD Change %
        df['ytd_change'] = (df['close'] - df['close_ytd_start']) / df['close_ytd_start'] * 100
        
        # Aggregation by Industry Group
        # We ignore rows with missing industry_group
        grp_df = df[df['industry_group'].notna() & (df['industry_group'] != '')].copy()
        
        # Aggregation Logic
        summary = grp_df.groupby('industry_group').agg({
            'symbol': 'count', # Number of stocks
            'market_cap_bil': 'sum', # Total Val in Billions
            'ytd_change': 'mean', # Avg % Chg YTD
            'sector': 'first' # Just take one
        }).reset_index()
        
        summary.rename(columns={'symbol': 'number_of_stocks'}, inplace=True)
        
        # Calculate "Performance Score" for Ranking
        # The user wants "Ind Group Rank". Usually based on weighted moving average of price performance.
        # For now, let's use YTD Change as the primary ranking factor, or maybe 6-month RS if available?
        # The user script calculate_ibd_metrics.py calculates 6-Month % change.
        # Let's check calculate_ibd_metrics logic: it uses avg(pct_change_6m) of stocks.
        # Let's calculate avg 6m change here too to be robust.
        
        # Actually, let's keep it simple: Rank by YTD Change for now provided in requirement " % Chg YTD"
        # Wait, IBD ranking is usually a complex proprietary formula (Price performance over last 6 months weighted).
        # Let's use YTD change as the proxy for "RS Score" of the group for this version.
        
        summary['rs_score'] = summary['ytd_change']  # Proxy
        
        # Fill NaNs
        summary['rs_score'] = summary['rs_score'].fillna(-999)
        summary['market_cap_bil'] = summary['market_cap_bil'].fillna(0)
        summary['ytd_change'] = summary['ytd_change'].fillna(0)
        
        # Rank (Descending: Higher Score is Rank 1)
        summary['rank'] = summary['rs_score'].rank(ascending=False, method='min')
        
        return summary

    def get_historical_ranks(self, current_summary, target_date):
        """
        Look up historical ranks from DB
        """
        # Dates
        d_1w = target_date - timedelta(weeks=1)
        d_3m = target_date - timedelta(weeks=12)
        d_6m = target_date - timedelta(weeks=26)
        
        # Helper to fetch ranks for a specific date (or closest before)
        def fetch_ranks_at(d):
            # Find closest date <= d
            latest_avail = self.db.query(func.max(IndustryGroupHistory.date)).filter(IndustryGroupHistory.date <= d).scalar()
            if not latest_avail:
                return {}
            
            rows = self.db.query(IndustryGroupHistory.industry_group, IndustryGroupHistory.rank).filter(IndustryGroupHistory.date == latest_avail).all()
            return {r.industry_group: r.rank for r in rows}

        ranks_1w = fetch_ranks_at(d_1w)
        ranks_3m = fetch_ranks_at(d_3m)
        ranks_6m = fetch_ranks_at(d_6m)
        
        # Merge
        current_summary['rank_1_week_ago'] = current_summary['industry_group'].map(ranks_1w)
        current_summary['rank_3_months_ago'] = current_summary['industry_group'].map(ranks_3m)
        current_summary['rank_6_months_ago'] = current_summary['industry_group'].map(ranks_6m)
        
        return current_summary

    def save(self, summary_df, target_date):
        logger.info(f"💾 Saving {len(summary_df)} Groups for {target_date}...")
        
        for idx, row in summary_df.iterrows():
            # Check if exists
            existing = self.db.query(IndustryGroupHistory).filter(
                IndustryGroupHistory.date == target_date,
                IndustryGroupHistory.industry_group == row['industry_group']
            ).first()
            
            if not existing:
                existing = IndustryGroupHistory(
                    date=target_date,
                    industry_group=row['industry_group']
                )
                self.db.add(existing)
            
            # Update fields
            existing.sector = row['sector']
            existing.number_of_stocks = int(row['number_of_stocks'])
            existing.market_value = float(row['market_cap_bil'])
            existing.ytd_change_percent = float(row['ytd_change'])
            existing.rs_score = float(row['rs_score'])
            existing.rank = int(row['rank'])
            
            # Historicals (Handle NaN)
            existing.rank_1_week_ago = int(row['rank_1_week_ago']) if pd.notna(row['rank_1_week_ago']) else None
            existing.rank_3_months_ago = int(row['rank_3_months_ago']) if pd.notna(row['rank_3_months_ago']) else None
            existing.rank_6_months_ago = int(row['rank_6_months_ago']) if pd.notna(row['rank_6_months_ago']) else None
            
        self.db.commit()
        logger.info("✅ Saved successfully.")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="YYYY-MM-DD")
    parser.add_argument("--backfill", action="store_true", help="Calculate for past dates?")
    args = parser.parse_args()
    
    db = SessionLocal()
    calc = IndustryGroupCalculator(db)
    
    dates_to_process = []
    
    if args.date:
        dates_to_process.append(datetime.strptime(args.date, "%Y-%m-%d").date())
    elif args.backfill:
        # Generate weekly dates for last 6 months
        today = date.today()
        current = today
        start = today - timedelta(days=365)
        while current >= start:
            dates_to_process.append(current)
            current -= timedelta(weeks=1)
            # Adjust to avoid weekends? The loader handles "closest price".
    else:
        # Default: Today
        # Check if today is weekend?
        dates_to_process.append(date.today())
        
    # Process sorted by date asc (so we build history)
    dates_to_process.sort()
    
    for d in dates_to_process:
        try:
            logger.info(f"🚀 Processing {d}...")
            df = calc.load_metric_data(d)
            if df.empty:
                logger.warning("No data found.")
                continue
                
            summary = calc.calculate_metrics(df)
            summary = calc.get_historical_ranks(summary, d)
            calc.save(summary, d)
            
        except Exception as e:
            logger.error(f"Failed for {d}: {e}")
            import traceback
            traceback.print_exc()
            
    db.close()

if __name__ == "__main__":
    main()
