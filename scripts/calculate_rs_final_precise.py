import pandas as pd
import numpy as np
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine, text
import time
import sys
import gc
import os
import psutil
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError
import gc
import psycopg2
import csv
from io import StringIO
from pathlib import Path

# Add project root to sys.path to allow importing from 'app'
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Reduce logging for performance
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class RSCalculatorUltraFast:
    def __init__(self, db_url):
        self.db_url = db_url
        self.engine = None
        self._reconnect()
        self._create_checkpoint_table()
        self.cache = {}
    
    def _reconnect(self):
        """إعادة الاتصال بقاعدة البيانات"""
        try:
            if self.engine:
                try:
                    self.engine.dispose()
                except:
                    pass
            
            # إعدادات محسنة للاتصال مع Render
            self.engine = create_engine(
                self.db_url,
                poolclass=QueuePool,
                pool_size=2,  # حجم أصغر للـ pool
                max_overflow=2,
                pool_recycle=300,  # إعادة التدوير كل 5 دقائق
                pool_pre_ping=True,  # التحقق من الاتصال قبل الاستخدام
                pool_timeout=30,
                connect_args={
                    'connect_timeout': 10,
                    'keepalives': 1,
                    'keepalives_idle': 30,
                    'keepalives_interval': 10,
                    'keepalives_count': 5,
                    'sslmode': 'require'
                }
            )
            logger.debug("✅ Database connection reinitialized")
        except Exception as e:
            logger.error(f"❌ Failed to reconnect: {e}")
            raise
    
    def _test_connection(self):
        """اختبار الاتصال بقاعدة البيانات"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.warning(f"⚠️  Connection test failed: {e}")
            return False
    
    def _execute_with_retry(self, sql, params=None, max_retries=3):
        """تنفيذ استعلام مع إعادة المحاولة عند الفشل"""
        for attempt in range(max_retries):
            try:
                if not self._test_connection():
                    logger.info(f"🔁 Attempting to reconnect (attempt {attempt + 1}/{max_retries})")
                    self._reconnect()
                    time.sleep(2 ** attempt)  # Exponential backoff
                
                with self.engine.connect() as conn:
                    result = conn.execute(text(sql), params or {})
                    conn.commit()
                    return result
            except OperationalError as e:
                logger.warning(f"⚠️  Operational error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"⏳ Waiting before retry...")
                    time.sleep(5)
                    continue
                else:
                    raise
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                raise
    
    def _create_checkpoint_table(self):
        """Create checkpoint table"""
        try:
            self._execute_with_retry("""
                CREATE TABLE IF NOT EXISTS calculation_checkpoint (
                    id SERIAL PRIMARY KEY,
                    last_date DATE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        except Exception as e:
            logger.warning(f"Could not create checkpoint table: {e}")
    
    def show_progress(self):
        """Show progress quickly"""
        try:
            # Total days
            result = self._execute_with_retry("""
                SELECT COUNT(DISTINCT date) 
                FROM prices 
                WHERE date >= '2003-01-01'
            """)
            total_days = result.scalar() or 0
            
            # Calculated days
            result = self._execute_with_retry("""
                SELECT COUNT(DISTINCT date) 
                FROM rs_daily 
                WHERE rs_rating IS NOT NULL
            """)
            calculated_days = result.scalar() or 0
            
            # Total ratings
            result = self._execute_with_retry("""
                SELECT COUNT(*) 
                FROM rs_daily 
                WHERE rs_rating IS NOT NULL
            """)
            total_ratings = result.scalar() or 0
            
            # Latest calculated date
            result = self._execute_with_retry("""
                SELECT MAX(date) 
                FROM rs_daily 
                WHERE rs_rating IS NOT NULL
            """)
            latest_date = result.scalar()
            
            # Last checkpoint
            try:
                result = self._execute_with_retry("SELECT MAX(last_date) FROM calculation_checkpoint")
                checkpoint = result.scalar()
            except:
                checkpoint = None
            
            print(f"\n📊 **Progress Report:**")
            print(f"   📅 Total Days: {total_days:,}")
            print(f"   ✅ Calculated Days: {calculated_days:,}")
            
            if total_days > 0:
                completion = (calculated_days / total_days) * 100
                print(f"   📈 Completion: {completion:.1f}%")
            
            print(f"   📊 Total Ratings: {total_ratings:,}")
            
            if latest_date:
                print(f"   🕐 Last Calculated Date: {latest_date}")
            
            if checkpoint:
                print(f"   📍 Last Checkpoint: {checkpoint}")
            
            remaining = total_days - calculated_days
            if remaining > 0:
                print(f"   ⏳ Remaining Days: {remaining:,}")
                # Faster estimate (0.5 seconds/day)
                print(f"   🚀 Estimated Time: ~{remaining * 0.5 / 60:.1f} minutes")
            
            return total_days, calculated_days
            
        except Exception as e:
            print(f"⚠️  Error showing progress: {e}")
            return 0, 0
    
    def save_checkpoint(self, last_date):
        """Save checkpoint with verification and retry"""
        try:
            # First, verify the date actually has data in rs_daily
            result = self._execute_with_retry("""
                SELECT EXISTS(
                    SELECT 1 FROM rs_daily 
                    WHERE date = :date AND rs_rating IS NOT NULL
                )
            """, {'date': last_date})
            
            date_has_data = result.scalar()
            
            if not date_has_data:
                logger.warning(f"⚠️  Cannot save checkpoint: Date {last_date} has no RS ratings yet")
                return
            
            # Save checkpoint with retry
            self._execute_with_retry("DELETE FROM calculation_checkpoint")
            self._execute_with_retry("""
                INSERT INTO calculation_checkpoint (last_date) 
                VALUES (:last_date)
            """, {'last_date': last_date})
            
            logger.info(f"✅ Checkpoint saved for date: {last_date}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save checkpoint: {e}")
    
    def get_last_checkpoint(self):
        """Get last checkpoint date"""
        try:
            result = self._execute_with_retry("SELECT MAX(last_date) FROM calculation_checkpoint")
            return result.scalar()
        except Exception as e:
            logger.debug(f"ℹ️  Could not get checkpoint: {e}")
            return None
    
    def calculate_daily_rs_ultrafast(self, target_date):
        """Calculate RS for a specific day - 10x faster"""
        
        # 1. Single SQL query to get all required data
        query = """
            WITH stock_list AS (
                SELECT DISTINCT symbol, company_name, industry_group
                FROM prices 
                WHERE date = :target_date
            ),
            price_data AS (
                SELECT 
                    p.symbol,
                    p.date,
                    p.close,
                    LAG(p.close, 63) OVER (PARTITION BY p.symbol ORDER BY p.date) as price_3m_ago,
                    LAG(p.close, 126) OVER (PARTITION BY p.symbol ORDER BY p.date) as price_6m_ago,
                    LAG(p.close, 189) OVER (PARTITION BY p.symbol ORDER BY p.date) as price_9m_ago,
                    LAG(p.close, 252) OVER (PARTITION BY p.symbol ORDER BY p.date) as price_12m_ago
                FROM prices p
                WHERE p.symbol IN (SELECT symbol FROM stock_list)
                    AND p.date <= :target_date
                    AND p.date >= :target_date - INTERVAL '13 months'
            ),
            current_data AS (
                SELECT 
                    pd.symbol,
                    sl.company_name,
                    sl.industry_group,
                    pd.date,
                    pd.close as current_price,
                    pd.price_3m_ago,
                    pd.price_6m_ago,
                    pd.price_9m_ago,
                    pd.price_12m_ago
                FROM price_data pd
                JOIN stock_list sl ON pd.symbol = sl.symbol
                WHERE pd.date = :target_date
                    -- Only require 3 months of history minimum to calculate RS
                    AND pd.price_3m_ago IS NOT NULL
            )
            SELECT 
                symbol,
                company_name,
                industry_group,
                date,
                current_price,
                -- Calculate returns as FLOAT
                CAST((current_price - price_3m_ago) / price_3m_ago AS FLOAT) as return_3m,
                CAST((current_price - price_6m_ago) / price_6m_ago AS FLOAT) as return_6m,
                CAST((current_price - price_9m_ago) / price_9m_ago AS FLOAT) as return_9m,
                CAST((current_price - price_12m_ago) / price_12m_ago AS FLOAT) as return_12m
            FROM current_data
            WHERE price_3m_ago > 0 
                AND current_price > 0
            ORDER BY symbol
        """
        
        try:
            # Execute single query with retry
            result = self._execute_with_retry(query, {'target_date': target_date})
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            if len(df) == 0:
                return []
            
            # CONVERT all to float to avoid Decimal issues
            numeric_cols = ['current_price', 'return_3m', 'return_6m', 'return_9m', 'return_12m']
            for col in numeric_cols:
                # Handle None/NaN before conversion
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 2. Calculate RS Raw using vectorization (super fast)
            # 2. Calculate Ranks for EACH period independently FIRST (Excel Logic)
            # This matches: PERCENTRANK.INC for each change% period
            period_ranks = {}
            for period in ['3m', '6m', '9m', '12m']:
                col_name = f'return_{period}'
                values = df[col_name].values
                valid_mask = ~np.isnan(values)
                
                # Initialize with NaN
                period_ranks[period] = np.full(len(df), np.nan)
                
                if valid_mask.sum() > 0:
                    valid_values = values[valid_mask]
                    # Sort indices
                    sorted_indices = np.argsort(valid_values)
                    
                    # Calculate rank pct (0 to 1)
                    ranks = np.empty_like(sorted_indices)
                    ranks[sorted_indices] = np.arange(len(valid_values))
                    
                    # Convert to percentile 1-99
                    if len(valid_values) > 1:
                        percentiles = (ranks / (len(valid_values) - 1)) * 100
                    else:
                        percentiles = np.array([50]) # Fallback for single item
                        
                    period_ranks[period][valid_mask] = np.clip(np.round(percentiles), 1, 99)
                
                # Assign to dataframe for saving/debugging
                df[f'rank_{period}'] = pd.Series(period_ranks[period]).fillna(-1).astype(int).replace({-1: None})

            # 3. Calculate Final RS Rating as Weighted Average of Ranks (Dynamic Weights)
            # Weights: 3m (40%), 6m (20%), 9m (20%), 12m (20%)
            
            weights = {'3m': 0.40, '6m': 0.20, '9m': 0.20, '12m': 0.20}
            
            numerator = np.zeros(len(df))
            denominator = np.zeros(len(df))
            
            for period, weight in weights.items():
                ranks = period_ranks[period]
                mask = ~np.isnan(ranks)
                
                # Add weighted rank where available
                numerator[mask] += ranks[mask] * weight
                denominator[mask] += weight
            
            # Calculate final score only where we have at least some data (denominator > 0)
            valid_score_mask = denominator > 0
            final_score = np.zeros(len(df))
            
            # Normalize the score: sum(weighted_ranks) / sum(valid_weights)
            # e.g. if only 3m (0.4) exists: score = (rank * 0.4) / 0.4 = rank
            # e.g. if 3m(0.4) and 6m(0.2) exist: score = (r3*0.4 + r6*0.2) / 0.6
            final_score[valid_score_mask] = numerator[valid_score_mask] / denominator[valid_score_mask]
            final_score[~valid_score_mask] = np.nan
            
            # Round up as per Excel Formula: ROUNDUP(value, 0)
            df['rs_rating'] = np.ceil(final_score)
            
            # Store the calculated score as 'rs_raw' for reference
            df['rs_raw'] = final_score

            # 4. Cleanup and Formatting
            # Fill NaN with -1 for integer conversion then replace with None
            df['rs_rating'] = df['rs_rating'].fillna(-1).astype(int).replace({-1: None})
            
            # 5. Prepare results
            results = []
            for _, row in df.iterrows():
                results.append({
                    'symbol': str(row['symbol']),
                    'date': row['date'],
                    'current_price': float(row['current_price']),
                    'return_3m': float(row['return_3m']),
                    'return_6m': float(row['return_6m']),
                    'return_9m': float(row['return_9m']),
                    'return_12m': float(row['return_12m']),
                    'rs_raw': float(row['rs_raw']),
                    'rs_rating': row.get('rs_rating'),
                    'rank_3m': row.get('rank_3m'),
                    'rank_6m': row.get('rank_6m'),
                    'rank_9m': row.get('rank_9m'),
                    'rank_12m': row.get('rank_12m'),
                    'company_name': str(row['company_name']),
                    'industry_group': str(row['industry_group']),
                    'has_complete_data': not np.isnan(row['rs_raw'])
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating RS for {target_date}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def save_results_batch(self, results):
        """Save results quickly with duplicate handling and fallback"""
        if not results:
            return 0
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(results)
            
            # Remove duplicates - IMPORTANT FIX
            df = df.drop_duplicates(subset=['symbol', 'date'], keep='last')
            
            # Filter only complete data
            df_complete = df[df['has_complete_data']].copy()
            
            if len(df_complete) == 0:
                return 0
            
            # Select only required columns
            df_to_save = df_complete[[
                'symbol', 'date', 'rs_rating', 'rs_raw',
                'return_3m', 'return_6m', 'return_9m', 'return_12m',
                'rank_3m', 'rank_6m', 'rank_9m', 'rank_12m',
                'company_name', 'industry_group'
            ]]
            
            # Try bulk insert first
            try:
                return self._save_bulk(df_to_save)
            except Exception as bulk_error:
                logger.warning(f"⚠️  Bulk save failed, trying simple save: {bulk_error}")
                return self._save_simple(df_to_save)
            
        except Exception as e:
            logger.error(f"Batch save failed: {e}")
            return 0
    
    def _save_bulk(self, df):
        """Bulk save using direct INSERT with ON CONFLICT DO UPDATE"""
        if df.empty:
            return 0
        
        # Convert DataFrame to records and handle NaN -> None
        df_clean = df.fillna(value=np.nan).replace({np.nan: None})
        data = df_clean.to_dict('records')
        
        stmt = """
            INSERT INTO rs_daily_v2 
            (symbol, date, rs_rating, rs_raw, return_3m, return_6m, return_9m, return_12m,
             rank_3m, rank_6m, rank_9m, rank_12m, company_name, industry_group)
            VALUES (:symbol, :date, :rs_rating, :rs_raw, :return_3m, :return_6m, :return_9m, :return_12m,
             :rank_3m, :rank_6m, :rank_9m, :rank_12m, :company_name, :industry_group)
            ON CONFLICT (symbol, date) DO UPDATE SET
            rs_rating = EXCLUDED.rs_rating,
            rs_raw = EXCLUDED.rs_raw,
            return_3m = EXCLUDED.return_3m,
            return_6m = EXCLUDED.return_6m,
            return_9m = EXCLUDED.return_9m,
            return_12m = EXCLUDED.return_12m,
            rank_3m = EXCLUDED.rank_3m,
            rank_6m = EXCLUDED.rank_6m,
            rank_9m = EXCLUDED.rank_9m,
            rank_12m = EXCLUDED.rank_12m,
            industry_group = EXCLUDED.industry_group
        """
        
        with self.engine.begin() as conn:
            conn.execute(text(stmt), data)
            
        return len(df)

    def _save_simple(self, df):
        # Uses same logic now as backup
        return self._save_bulk(df)


    def setup_table(self):
        """Setup V2 table with retry using explicit transaction"""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS rs_daily_v2 (
                        id SERIAL PRIMARY KEY,
                        symbol VARCHAR(20),
                        date DATE,
                        rs_rating INTEGER,
                        rs_raw DECIMAL(10, 6),
                        return_3m DECIMAL(10, 6),
                        return_6m DECIMAL(10, 6),
                        return_9m DECIMAL(10, 6),
                        return_12m DECIMAL(10, 6),
                        rank_3m INTEGER,
                        rank_6m INTEGER,
                        rank_9m INTEGER,
                        rank_12m INTEGER,
                        company_name VARCHAR(255),
                        industry_group VARCHAR(255),
                        UNIQUE(symbol, date)
                    )
                """))
                
                # Create indexes for V2
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_rs_v2_symbol_date ON rs_daily_v2(symbol, date)",
                    "CREATE INDEX IF NOT EXISTS idx_rs_v2_date_rating ON rs_daily_v2(date, rs_rating DESC)",
                    "CREATE INDEX IF NOT EXISTS idx_rs_v2_date ON rs_daily_v2(date)"
                ]
                
                for idx in indexes:
                    try:
                        conn.execute(text(idx))
                    except Exception as e:
                        logger.warning(f"Index creation warning: {e}")
            
            print("✅ Table rs_daily_v2 verified/created successfully")
                    
        except Exception as e:
            logger.error(f"Error setting up table: {e}")
            

    
    def calculate_historical_ultrafast(self, start_date='2003-01-01', batch_size=200):
        """Ultra-fast historical calculation with error handling"""
        
        total_days, calculated_days = self.show_progress()
        
        if calculated_days >= total_days and total_days > 0:
            print("🎉 All days already calculated!")
            return
        
        print(f"🚀 Starting ultra-fast calculation from {start_date}")
        
        # Get remaining dates
        try:
            result = self._execute_with_retry("""
                SELECT DISTINCT p.date
                FROM prices p
                WHERE p.date >= :start_date 
                    AND p.date NOT IN (
                        SELECT DISTINCT date 
                        FROM rs_daily 
                        WHERE rs_rating IS NOT NULL
                    )
                ORDER BY p.date
            """, {'start_date': start_date})
            
            dates = [row[0] for row in result.fetchall()]
            
        except Exception as e:
            logger.error(f"❌ Failed to get dates: {e}")
            return
        
        if not dates:
            print("🎉 No days to calculate!")
            return
        
        remaining_days = len(dates)
        print(f"📊 Remaining Days: {remaining_days:,}")
        
        # Create table if doesn't exist
        self.setup_table()
        
        start_time = time.time()
        total_saved = 0
        
        # Split days into large batches
        date_batches = [dates[i:i + batch_size] for i in range(0, remaining_days, batch_size)]
        
        for batch_num, date_batch in enumerate(date_batches, 1):
            batch_start_time = time.time()
            batch_saved = 0
            last_successful_date = None
            
            print(f"\n{'='*60}")
            print(f"⚡ Batch {batch_num}/{len(date_batches)}")
            print(f"📅 From {date_batch[0]} to {date_batch[-1]}")
            print(f"🔢 Days in Batch: {len(date_batch)}")
            print(f"{'='*60}")
            
            for target_date in date_batch:
                try:
                    # Test connection before calculation
                    if not self._test_connection():
                        logger.info("🔄 Reconnecting to database...")
                        self._reconnect()
                        time.sleep(1)
                    
                    # Calculate RS using ultra-fast method
                    results = self.calculate_daily_rs_ultrafast(target_date)
                    
                    # Save results
                    saved_count = self.save_results_batch(results)
                    
                    if saved_count > 0:
                        batch_saved += saved_count
                        # Only update checkpoint if data was actually saved
                        last_successful_date = target_date
                        print(f"✓ {target_date}: {saved_count} stocks", end='\r')
                    else:
                        print(f"⚠️ {target_date}: No data saved", end='\r')
                    
                    # Small delay to avoid overwhelming the database
                    time.sleep(0.1)
                    
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error(f"✗ {target_date}: {e}")
                    # Try to reconnect on error
                    try:
                        self._reconnect()
                    except:
                        pass
                    continue
            
            total_saved += batch_saved
            
            # Save checkpoint after each batch - ONLY if we have a successful date
            if last_successful_date:
                try:
                    self.save_checkpoint(last_successful_date)
                    print(f"\n💾 Checkpoint saved: {last_successful_date}")
                except Exception as e:
                    logger.error(f"Failed to save checkpoint: {e}")
            else:
                print(f"\n⚠️  No checkpoint saved (no successful calculations in this batch)")
            
            # Batch report
            batch_elapsed = time.time() - batch_start_time
            if len(date_batch) > 0:
                avg_time_per_day = batch_elapsed / len(date_batch)
            else:
                avg_time_per_day = 0
            
            print(f"\n📊 Batch {batch_num} Report:")
            print(f"   ✅ Stocks Saved: {batch_saved:,}")
            print(f"   ⏱️  Batch Time: {batch_elapsed:.1f} seconds")
            if avg_time_per_day > 0:
                print(f"   🚀 Speed: {avg_time_per_day:.2f} seconds/day")
            
            # Memory cleanup
            gc.collect()
            
            # Estimate remaining time
            remaining_batches = len(date_batches) - batch_num
            if remaining_batches > 0 and avg_time_per_day > 0:
                est_remaining = (remaining_batches * batch_elapsed) / 60
                print(f"   ⏳ Estimated Time Remaining: {est_remaining:.1f} minutes")
        
        # Final report
        total_elapsed = (time.time() - start_time) / 60
        
        print(f"\n{'='*80}")
        print(f"🎉 Calculation completed successfully!")
        print(f"{'='*80}")
        print(f"📊 Statistics:")
        print(f"   📅 Calculated Days: {remaining_days}")
        print(f"   ✅ Total Stocks Saved: {total_saved:,}")
        print(f"   ⏱️  Total Time: {total_elapsed:.1f} minutes")
        if remaining_days > 0:
            print(f"   🚀 Average Speed: {total_elapsed*60/remaining_days:.2f} seconds/day")
        print(f"{'='*80}")
    
    def setup_table(self):
        """Setup table with retry"""
        try:
            self._execute_with_retry("""
                CREATE TABLE IF NOT EXISTS rs_daily (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20),
                    date DATE,
                    rs_rating INTEGER,
                    rs_raw DECIMAL(10, 6),
                    return_3m DECIMAL(10, 6),
                    return_6m DECIMAL(10, 6),
                    return_9m DECIMAL(10, 6),
                    return_12m DECIMAL(10, 6),
                    rank_3m INTEGER,
                    rank_6m INTEGER,
                    rank_9m INTEGER,
                    rank_12m INTEGER,
                    company_name VARCHAR(255),
                    industry_group VARCHAR(255),
                    UNIQUE(symbol, date)
                )
            """)
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_rs_symbol_date ON rs_daily(symbol, date)",
                "CREATE INDEX IF NOT EXISTS idx_rs_date_rating ON rs_daily(date, rs_rating DESC)",
                "CREATE INDEX IF NOT EXISTS idx_rs_date ON rs_daily(date)"
            ]
            
            for idx in indexes:
                try:
                    self._execute_with_retry(idx)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error setting up table: {e}")
    
    def continue_from_checkpoint(self):
        """Continue from last checkpoint - FIXED VERSION"""
        last_checkpoint = self.get_last_checkpoint()
        
        if last_checkpoint:
            print(f"📍 Continuing from checkpoint: {last_checkpoint}")
            
            # Get the ACTUAL last calculated date from rs_daily
            try:
                result = self._execute_with_retry("""
                    SELECT MAX(date) 
                    FROM rs_daily 
                    WHERE rs_rating IS NOT NULL
                """)
                actual_last_date = result.scalar()
            except:
                actual_last_date = None
            
            if actual_last_date:
                print(f"📊 Actual last calculated date: {actual_last_date}")
                
                # Use the later date (checkpoint or actual)
                start_date = max(last_checkpoint, actual_last_date)
                print(f"🎯 Starting from: {start_date}")
                
                # Start from the next day
                next_date = start_date + pd.Timedelta(days=1)
                self.calculate_historical_ultrafast(
                    start_date=next_date.strftime('%Y-%m-%d'),
                    batch_size=200
                )
            else:
                # No data at all, start from checkpoint
                next_date = last_checkpoint + pd.Timedelta(days=1)
                self.calculate_historical_ultrafast(
                    start_date=next_date.strftime('%Y-%m-%d'),
                    batch_size=200
                )
        else:
            print("ℹ️  No checkpoint found, getting last calculated date...")
            
            # Get the actual last calculated date
            try:
                result = self._execute_with_retry("""
                    SELECT MAX(date) 
                    FROM rs_daily 
                    WHERE rs_rating IS NOT NULL
                """)
                last_calculated = result.scalar()
            except:
                last_calculated = None
            
            if last_calculated:
                print(f"📌 Last calculated date found: {last_calculated}")
                next_date = last_calculated + pd.Timedelta(days=1)
                self.calculate_historical_ultrafast(
                    start_date=next_date.strftime('%Y-%m-%d'),
                    batch_size=200
                )
            else:
                print("ℹ️  No data found, starting from beginning")
                self.calculate_historical_ultrafast(batch_size=200)


    def calculate_full_history_optimized(self):
        """Calculate RS for ALL history using in-memory vectorization (The Rocket Approach 🚀)"""
        
        print("📥 Loading ALL price history into memory... (This might take a minute)")
        
        # 1. Fetch simplified data (Date, Symbol, Close)
        query = """
            SELECT date, symbol, close 
            FROM prices 
            WHERE date >= '2000-01-01'
                AND close > 0
            ORDER BY date
        """
        try:
            # Load directly into DataFrame using connection
            with self.engine.connect() as conn:
                df_prices = pd.read_sql(text(query), conn)
            print(f"✅ Loaded {len(df_prices):,} price records")
            
            if df_prices.empty:
                print("❌ No data found!")
                return None

            # 2. Pivot to Wide Format (Rows=Date, Cols=Symbol)
            print("🔄 Pivoting data for vectorized calculation...")
            df_wide = df_prices.pivot(index='date', columns='symbol', values='close')
            df_wide = df_wide.sort_index()
            
            # Replace any remaining zeros with tiny value to avoid division by zero
            df_wide = df_wide.replace(0, 0.000001)
            
            periods = {
                '3m': 63,
                '6m': 126,
                '9m': 189,
                '12m': 252
            }
            
            # 3. Calculate Returns Vectorized
            print("📈 Calculating returns for all periods...")
            returns_dfs = {}
            for name, days in periods.items():
                print(f"   Calculating {name} ({days} days)...")
                ret_df = df_wide.pct_change(periods=days)
                ret_df = ret_df.replace([np.inf, -np.inf], np.nan)
                returns_dfs[name] = ret_df

            # 4. Stack back to Long Format to calculate Ranks
            print("📊 Stacking data and calculating ranks...")
            
            def melt_returns(ret_df, col_name):
                s = ret_df.stack(dropna=False)
                s.name = col_name
                return s

            df_all = pd.concat([
                melt_returns(returns_dfs['3m'], 'return_3m'),
                melt_returns(returns_dfs['6m'], 'return_6m'),
                melt_returns(returns_dfs['9m'], 'return_9m'),
                melt_returns(returns_dfs['12m'], 'return_12m'),
                melt_returns(df_wide, 'current_price')
            ], axis=1)
            
            df_all = df_all.reset_index()
            
            original_len = len(df_all)
            # RELAXED FILTER: Keep rows with at least 3m return
            df_all = df_all.dropna(subset=['return_3m'])
            print(f"   Filtered valid rows: {len(df_all):,} (from {original_len:,})")
            
            if len(df_all) == 0:
                print("⚠️ No valid rows after filtering!")
                return None

            # 5. Calculate Ranks PER DATE
            print("🏆 Calculating Daily Ranks (1-99)...")
            
            for p in periods.keys():
                col = f'return_{p}'
                rank_col = f'rank_{p}'
                # Convert to numeric, errors='coerce' turns non-numeric to NaN
                df_all[col] = pd.to_numeric(df_all[col], errors='coerce')
                
                # Calculate rank only on valid numeric values
                # groupby(date) respects the date index or column
                # we need to ensure we don't rank NaNs as 100 or something wrong
                # rank(pct=True) naturally handles NaNs by ignoring them in calculation but keeping them as NaN in output if na_option='keep' (default)
                df_all[rank_col] = df_all.groupby('date')[col].rank(pct=True, method='average') * 100
                
                # Fill missing ranks with -1 for now, then clip valid ones
                # We do NOT want to fill NaNs with 50 here because that would imply average performance for missing data
                # Instead, leave them as NaN so they are ignored in the weighted average
                df_all[rank_col] = df_all[rank_col].round().clip(1, 99)

            # 6. Calculate Weighted RS (Dynamic Weights Logic)
            print("🧮 Calculating Final Weighted RS...")
            
            # Weighted Average allowing missing periods
            weights = {'3m': 0.40, '6m': 0.20, '9m': 0.20, '12m': 0.20}
            
            numerator = 0
            denominator = 0
            
            for p, w in weights.items():
                rank_col = f'rank_{p}'
                # Check where rank is NOT NaN
                mask = df_all[rank_col].notna()
                
                # Add to numerator and denominator where data exists
                numerator += df_all[rank_col].fillna(0) * (mask * w)
                denominator += mask * w
                
                # IMPORTANT: Convert ranks to Integer for DB saving
                # Floating point ranks (e.g. 94.0) cause DB errors in Integer columns
                df_all[rank_col] = df_all[rank_col].fillna(-1).astype(int).replace({-1: None})
            
            # Avoid division by zero
            final_score = np.where(denominator > 0, numerator / denominator, np.nan)
            
            # Assign to DataFrame
            df_all['rs_raw'] = final_score
            
            # Round up and fill NaNs
            # Use final_score (numpy array) directly to create the column first to avoid index alignment issues with pd.Series()
            # Or explicitly pass the index
            df_all['rs_rating'] = pd.Series(final_score, index=df_all.index)
            df_all['rs_rating'] = np.ceil(df_all['rs_rating']).clip(1, 99).fillna(-1).astype(int).replace({-1: None})
            
            # Add static metadata
            print("🔗 Merging static company info...")
            meta_query = "SELECT DISTINCT symbol, company_name, industry_group FROM prices"
            with self.engine.connect() as conn:
                df_meta = pd.read_sql(text(meta_query), conn)
            df_meta = df_meta.drop_duplicates(subset=['symbol'], keep='last')
            
            df_final = pd.merge(df_all, df_meta, on='symbol', how='left')
            
            print(f"✅ Final DataFrame ready with {len(df_final):,} rows")
            return df_final
            
        except Exception as e:
            logger.error(f"❌ Error in vectorized calculation: {e}")
            import traceback
            traceback.print_exc()
            return None


    def save_with_copy_protocol(self, df):
        """Ultra-fast save using PostgreSQL COPY protocol (50x faster)"""
        if df is None or df.empty:
            print("❌ No data to save!")
            return
        
        print(f"🚀 ULTRA-FAST COPY: Saving {len(df):,} records...")
        
        # الأعمدة المطلوبة
        cols_to_save = [
            'symbol', 'date', 'rs_rating', 'rs_raw',
            'return_3m', 'return_6m', 'return_9m', 'return_12m',
            'rank_3m', 'rank_6m', 'rank_9m', 'rank_12m',
            'company_name', 'industry_group'
        ]
        
        # تأكد من وجود الأعمدة
        for col in cols_to_save:
            if col not in df.columns:
                df[col] = None
        
        # اختيار وتنظيف البيانات
        df_clean = df[cols_to_save].copy()
        
        # تحويل التواريخ لسلسلة نصية
        if 'date' in df_clean.columns:
            df_clean['date'] = df_clean['date'].astype(str)
        
        # استبدال NaN/None بقيم فارغة
        # COPY expects NULL as \N by default or empty string if specified
        # We will use explicit \N for clarity
        df_clean = df_clean.fillna('\\N')
        
        print(f"📦 Data prepared: {len(df_clean):,} rows")
        
        start_time = time.time()
        
        conn = None
        cur = None
        try:
            # استخراج بيانات الاتصال من URL
            # postgresql://user:password@host:port/database
            db_url = self.db_url.replace('postgresql://', '')
            if '@' not in db_url:
                 raise ValueError("Invalid DB URL format")
                 
            user_pass, host_db = db_url.split('@')
            user, password = user_pass.split(':')
            host_port, database = host_db.split('/')
            
            host = host_port
            port = '5432'
            if ':' in host_port:
                host, port = host_port.split(':')
            
            # اتصال مباشر بـ psycopg2
            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                sslmode='require'
            )
            
            cur = conn.cursor()
            
            # 1. مسح الجدول أولاً (لأن COPY أسرع مع جدول فارغ)
            # print("🧹 Truncating table for clean COPY...")
            # cur.execute("TRUNCATE TABLE rs_daily_v2")
            # لا داعي لـ TRUNCATE لأننا مسحناه في Main، ولكن احتياطاً
            
            # 2. تحضير البيانات في StringIO
            print("📝 Preparing COPY buffer...")
            output = StringIO()
            writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            
            # كتابة البيانات للـ Buffer
            # نكتب سطر سطر لتفادي مشاكل الذاكرة مع to_csv
            # أو الأسرع: استخدام to_csv الخاص بـ pandas
            # لكن csv.writer أدق في التعامل مع الـ Quoting
            
            # الأسرع فعلاً:
            for row in df_clean.itertuples(index=False):
                writer.writerow(row)
            
            output.seek(0)
            
            # 3. تنفيذ COPY
            print("⚡ Executing COPY (This is FAST!)...")
            copy_start = time.time()
            
            cur.copy_expert(f"""
                COPY rs_daily_v2 ({','.join(cols_to_save)})
                FROM STDIN
                WITH (FORMAT CSV, NULL '\\N')
            """, output)
            
            conn.commit()
            copy_time = time.time() - copy_start
            
            cur.execute("SELECT COUNT(*) FROM rs_daily_v2")
            count = cur.fetchone()[0]
            
            total_time = time.time() - start_time
            
            print(f"\n{'='*60}")
            print(f"🎉 COPY COMPLETED!")
            print(f"{'='*60}")
            print(f"📊 Statistics:")
            print(f"   ✅ Rows Inserted: {count:,}")
            print(f"   ⚡ COPY Time Only: {copy_time:.1f} seconds")
            print(f"   ⏱️  Total Time: {total_time/60:.1f} minutes")
            print(f"   🚀 Speed: {count/copy_time:,.0f} rows/second!")
            print(f"{'='*60}")
            
            return count
            
        except Exception as e:
            print(f"\n❌ COPY failed: {e}")
            if conn:
                conn.rollback()
            # Fallback
            print("\n🔄 Falling back to batched INSERT...")
            return self.save_bulk_results(df)
            
        finally:
            if cur: cur.close()
            if conn: conn.close()
            if 'output' in locals(): output.close()


    def save_bulk_results(self, df):
        """Save with optimized batch processing - 3x Faster"""
        if df is None or df.empty:
            print("❌ No data to save!")
            return
            
        print(f"💾 Saving {len(df):,} records (Optimized for Render)...")
        
        # الأعمدة المطلوبة
        cols_to_save = [
            'symbol', 'date', 'rs_rating', 'rs_raw',
            'return_3m', 'return_6m', 'return_9m', 'return_12m',
            'rank_3m', 'rank_6m', 'rank_9m', 'rank_12m',
            'company_name', 'industry_group'
        ]
        
        # تأكد من وجود الأعمدة
        print("📦 Preparing data...")
        for col in cols_to_save:
            if col not in df.columns:
                df[col] = None
        
        # اختيار الأعمدة فقط
        df_clean = df[cols_to_save].copy()
        
        # تنظيف البيانات بسرعة
        for col in df_clean.select_dtypes(include=[np.number]).columns:
            df_clean[col] = df_clean[col].astype(str).replace({'nan': None, 'inf': None, '-inf': None})
        
        print(f"   ✅ Data ready: {len(df_clean):,} rows")
        
        # إعدادات للحفظ الآمن والسريع
        chunk_size = 2500  # حجم آمن لـ Render
        total_saved = 0
        start_time = time.time()
        
        # إحصاءات التقدم
        chunk_times = []
        
        print(f"\n🚀 Uploading in chunks of {chunk_size}...")
        
        for i in range(0, len(df_clean), chunk_size):
            chunk = df_clean.iloc[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            total_chunks = (len(df_clean) + chunk_size - 1) // chunk_size
            
            chunk_start = time.time()
            
            try:
                # حفظ الدفعة
                saved = self._save_bulk_optimized(chunk)
                total_saved += saved
                
                # حساب الإحصاءات
                chunk_time = time.time() - chunk_start
                chunk_times.append(chunk_time)
                
                elapsed_total = time.time() - start_time
                progress = (i + len(chunk)) / len(df_clean) * 100
                avg_speed = saved / chunk_time if chunk_time > 0 else 0
                
                # وقت التباطؤ بين الدفعات لمنع الضغط على Render
                if chunk_num % 10 == 0:
                    time.sleep(2)  # استراحة كل 10 دفعات
                elif chunk_num % 5 == 0:
                    time.sleep(1)  # استراحة كل 5 دفعات
                
                print(f"   ✅ Chunk {chunk_num}/{total_chunks}: {saved} rows "
                      f"({progress:.1f}%) - {avg_speed:.0f} rows/sec")
                
                # تنظيف الذاكرة
                if chunk_num % 20 == 0:
                    gc.collect()
                    
            except Exception as e:
                print(f"\n❌ Error in chunk {chunk_num}: {e}")
                print("Retrying with smaller chunk...")
                
                # إعادة المحاولة بدفعات أصغر
                small_saved = self._retry_with_smaller_chunks(chunk)
                total_saved += small_saved
                print(f"   Recovered {small_saved}/{len(chunk)} rows")
        
        total_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"🎉 SAVING COMPLETED!")
        print(f"{'='*60}")
        print(f"� Statistics:")
        print(f"   ✅ Total Rows Saved: {total_saved:,}")
        print(f"   ⏱️  Total Time: {total_time/60:.1f} minutes")
        if total_time > 0:
            print(f"   🚀 Average Speed: {total_saved/total_time:.1f} rows/sec")
        print(f"{'='*60}")
        
        # التحقق من الجدول
        self._verify_save_results()

    def _save_bulk_optimized(self, df):
        """Optimized bulk save with connection pooling"""
        if df.empty:
            return 0
        
        # تحويل إلى سجلات مع تنظيف NaN
        data = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                # تحويل NaN/Inf إلى None
                if pd.isna(val) or val == 'None' or val == 'nan':
                     record[col] = None
                else:
                    record[col] = val
            data.append(record)
        
        stmt = """
            INSERT INTO rs_daily_v2 
            (symbol, date, rs_rating, rs_raw, return_3m, return_6m, return_9m, return_12m,
             rank_3m, rank_6m, rank_9m, rank_12m, company_name, industry_group)
            VALUES (:symbol, :date, :rs_rating, :rs_raw, :return_3m, :return_6m, :return_9m, :return_12m,
             :rank_3m, :rank_6m, :rank_9m, :rank_12m, :company_name, :industry_group)
            ON CONFLICT (symbol, date) DO UPDATE SET
            rs_rating = EXCLUDED.rs_rating,
            rs_raw = EXCLUDED.rs_raw,
            return_3m = EXCLUDED.return_3m,
            return_6m = EXCLUDED.return_6m,
            return_9m = EXCLUDED.return_9m,
            return_12m = EXCLUDED.return_12m,
            rank_3m = EXCLUDED.rank_3m,
            rank_6m = EXCLUDED.rank_6m,
            rank_9m = EXCLUDED.rank_9m,
            rank_12m = EXCLUDED.rank_12m,
            industry_group = EXCLUDED.industry_group
        """
        
        try:
            # استخدام اتصال منفصل مع إعدادات أفضل
            with self.engine.begin() as conn:
                conn.execute(text(stmt), data)
            return len(df)
        except Exception as e:
            # خطأ في الاتصال، حاول إعادة الاتصال
            print(f"   ⚠️  Connection error: {e}, reconnecting...")
            self._reconnect()
            time.sleep(2)
            raise

    def _retry_with_smaller_chunks(self, df):
        """Retry failed chunks with smaller sizes"""
        if df.empty:
            return 0
        
        small_saved = 0
        small_chunk_size = 500  # حجم صغير جداً
        
        for j in range(0, len(df), small_chunk_size):
            small_chunk = df.iloc[j:j + small_chunk_size]
            try:
                self._save_bulk_optimized(small_chunk)
                small_saved += len(small_chunk)
                time.sleep(0.5)  # استراحة بين الدفعات الصغيرة
            except Exception as e:
                print(f"     ⚠️  Failed small chunk: {e}")
                continue
        
        return small_saved

    def _verify_save_results(self):
        """Verify data was saved correctly"""
        try:
            with self.engine.connect() as conn:
                # عدد الصفوف
                result = conn.execute(text("SELECT COUNT(*) FROM rs_daily_v2"))
                count = result.scalar()
                print(f"🔍 Verification: rs_daily_v2 has {count:,} rows")
                
                # عدد الأيام المختلفة
                result = conn.execute(text("SELECT COUNT(DISTINCT date) FROM rs_daily_v2"))
                days = result.scalar()
                print(f"📅 Distinct Dates: {days}")
                
                # تاريخ البدء والنهاية
                result = conn.execute(text("SELECT MIN(date), MAX(date) FROM rs_daily_v2"))
                min_date, max_date = result.fetchone()
                print(f"📊 Date Range: {min_date} to {max_date}")
                
        except Exception as e:
            print(f"⚠️ Verification failed: {e}")



    def _check_database_health(self):
        """Check database health before heavy operations"""
        try:
            with self.engine.connect() as conn:
                # عدد الاتصالات النشطة
                result = conn.execute(text("""
                    SELECT count(*) as active_connections 
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """))
                active_conns = result.scalar()
                
                # استخدام الذاكرة
                result = conn.execute(text("""
                    SELECT setting::integer as max_connections 
                    FROM pg_settings 
                    WHERE name = 'max_connections'
                """))
                max_conns = result.scalar()
                
                print(f"🔍 Database Health: {active_conns}/{max_conns} active connections")
                
                if active_conns > max_conns * 0.8:
                    print(f"⚠️  Warning: High connection usage ({active_conns}/{max_conns})")
                    return False
                
                return True
                
        except Exception as e:
            print(f"⚠️  Could not check database health: {e}")
            return True  # تابع مع افتراض أن كل شيء بخير


def main():
    """Main function Optimized for V2"""
    
    # Import settings to get the correct DB URL (Same as app)
    from app.core.config import settings
    DB_URL = str(settings.DATABASE_URL)
    
    print("="*80)
    print("🚀 **RS Calculator - PANDAS VECTORIZED ENGINE (V2 Table)**")
    print("   Does 20 years of math in seconds. Saves to rs_daily_v2.")
    print("="*80)
    
    calculator = RSCalculatorUltraFast(DB_URL)
    
    # Menu
    print("\n📋Options:")
    print("1. 🧨 Full Recalculation (Batched INSERT - Safer)")
    print("2. ⚡ ULTRA-FAST COPY Method (Experimental - Super Fast!)")
    print("3. ✨ Incremental Update (Append only missing dates)")
    print("4. ❌ Exit")
    
    choice = input("\nChoose: ")
    
    if choice == '1':
        confirm = input("⚠️  Ready to build rs_daily_v2? (y/n): ")
        if confirm.lower() == 'y':
            # 1. Health Check
            if not calculator._check_database_health():
                print("❌ Database is under heavy load. Try again later.")
                return

            print("🧹 Resetting V2 table...")
            try:
                with calculator.engine.begin() as conn:
                    # Drop existing
                    conn.execute(text("DROP TABLE IF EXISTS rs_daily_v2 CASCADE"))
                    
                    # Create Fresh V2 Table (WITHOUT Indexes for speed)
                    conn.execute(text("""
                        CREATE TABLE rs_daily_v2 (
                            id SERIAL PRIMARY KEY,
                            symbol VARCHAR(20),
                            date DATE,
                            rs_rating INTEGER,
                            rs_raw DECIMAL(10, 6),
                            return_3m DECIMAL(10, 6),
                            return_6m DECIMAL(10, 6),
                            return_9m DECIMAL(10, 6),
                            return_12m DECIMAL(10, 6),
                            rank_3m INTEGER,
                            rank_6m INTEGER,
                            rank_9m INTEGER,
                            rank_12m INTEGER,
                            company_name VARCHAR(255),
                            industry_group VARCHAR(255),
                            UNIQUE(symbol, date)
                        )
                    """))
                    print("✅ Created fresh rs_daily_v2 table")
                    print("⏳ Index creation deferred for speed...")
                    
            except Exception as e:
                print(f"❌ Error recreating table: {e}")
                return

            # Calculate
            df_results = calculator.calculate_full_history_optimized()
            
            # Save
            if df_results is not None:
                calculator.save_bulk_results(df_results)

                # Create Indexes LAST (Fastest way)
                print("\n🔨 Creating indexes now...")
                try:
                    with calculator.engine.begin() as conn:
                        indexes = [
                            "CREATE INDEX IF NOT EXISTS idx_rs_v2_symbol_date ON rs_daily_v2(symbol, date)",
                            "CREATE INDEX IF NOT EXISTS idx_rs_v2_date_rating ON rs_daily_v2(date, rs_rating DESC)",
                            "CREATE INDEX IF NOT EXISTS idx_rs_v2_date ON rs_daily_v2(date)"
                        ]
                        for idx in indexes:
                            conn.execute(text(idx))
                        print("✅ Indexes created successfully")
                except Exception as e:
                    print(f"⚠️  Index creation warning: {e}")
                
        else:
            print("Cancelled.")
    
    elif choice == '2':  # ⚡ ULTRA-FAST COPY
        print("⚡ ULTRA-FAST COPY METHOD ACTIVATED!")
        print("⚠️  WARNING: This will DROP and recreate the table!")
        
        confirm = input("Continue? (y/n): ")
        if confirm.lower() == 'y':
            # 1. إنشاء الجدول
            print("🧹 Preparing table...")
            try:
                with calculator.engine.begin() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS rs_daily_v2 CASCADE"))
                    
                    conn.execute(text("""
                        CREATE TABLE rs_daily_v2 (
                            id SERIAL PRIMARY KEY,
                            symbol VARCHAR(20),
                            date DATE,
                            rs_rating INTEGER,
                            rs_raw DECIMAL(10, 6),
                            return_3m DECIMAL(10, 6),
                            return_6m DECIMAL(10, 6),
                            return_9m DECIMAL(10, 6),
                            return_12m DECIMAL(10, 6),
                            rank_3m INTEGER,
                            rank_6m INTEGER,
                            rank_9m INTEGER,
                            rank_12m INTEGER,
                            company_name VARCHAR(255),
                            industry_group VARCHAR(255),
                            UNIQUE(symbol, date)
                        )
                    """))
                    print("✅ Table created (no indexes yet)")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return
            
            # 2. الحساب
            df_results = calculator.calculate_full_history_optimized()
            
            if df_results is not None:
                # 3. الحفظ باستخدام COPY (السريع جداً)
                print("\n🚀 Starting COPY protocol...")
                saved = calculator.save_with_copy_protocol(df_results)
                
                if saved and saved > 0:
                    # 4. إنشاء الفهارس بعد التحميل
                    print("\n🔨 Creating indexes...")
                    try:
                        with calculator.engine.begin() as conn:
                            indexes = [
                                "CREATE INDEX idx_rs_v2_symbol_date ON rs_daily_v2(symbol, date)",
                                "CREATE INDEX idx_rs_v2_date_rating ON rs_daily_v2(date, rs_rating DESC)",
                                "CREATE INDEX idx_rs_v2_date ON rs_daily_v2(date)"
                            ]
                            for idx in indexes:
                                conn.execute(text(idx))
                            print("✅ All indexes created")
                    except Exception as e:
                        print(f"⚠️  Index warning: {e}")
        
        else:
            print("Cancelled.")

    elif choice == '3':
        print("\n📈 Starting Incremental Update...")
        
        # 1. Get latest date from DB
        latest_date = None
        try:
            with calculator.engine.connect() as conn:
                # Check if table exists
                table_check = conn.execute(text("SELECT to_regclass('public.rs_daily_v2')")).scalar()
                if table_check:
                    res = conn.execute(text("SELECT MAX(date) FROM rs_daily_v2")).scalar()
                    if res:
                        latest_date = res
                        print(f"📅 Latest DB Date: {latest_date}")
                    else:
                        print("⚠️ Table is empty. Will save all data.")
                else:
                    print("⚠️ Table 'rs_daily_v2' does not exist. Please run Option 1 first.")
                    return
        except Exception as e:
            print(f"❌ Error checking DB: {e}")
            return

        # 2. Calculate ALL (in memory - fast)
        df_results = calculator.calculate_full_history_optimized()
        
        if df_results is not None and not df_results.empty:
            # 3. Filter New Only
            if latest_date:
                # Ensure date format matches
                df_results['date'] = pd.to_datetime(df_results['date']).dt.date
                
                # Filter > latest_date
                df_new = df_results[df_results['date'] > latest_date]
                
                if df_new.empty:
                    print(f"✅ Database is up to date (Latest: {latest_date}). Nothing to add.")
                else:
                    print(f"📦 Found {len(df_new):,} new records (from {df_new['date'].min()} to {df_new['date'].max()})")
                    # 4. Save New Only
                    calculator.save_bulk_results(df_new)
            else:
                # Save all if DB was empty
                calculator.save_bulk_results(df_results)

    else:
        print("Bye.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  **User Stopped**")

        print("🔄 Run --resume to continue")
    except Exception as e:
        print(f"\n\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()