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
                    AND pd.price_3m_ago IS NOT NULL
                    AND pd.price_6m_ago IS NOT NULL
                    AND pd.price_9m_ago IS NOT NULL
                    AND pd.price_12m_ago IS NOT NULL
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
                AND price_6m_ago > 0 
                AND price_9m_ago > 0 
                AND price_12m_ago > 0
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
                df[col] = df[col].astype(float)
            
            # 2. Calculate RS Raw using vectorization (super fast)
            df['rs_raw'] = (
                df['return_3m'] * 0.4 +
                df['return_6m'] * 0.2 +
                df['return_9m'] * 0.2 +
                df['return_12m'] * 0.2
            )
            
            # 3. Calculate ratings for all periods at once
            for period in ['3m', '6m', '9m', '12m']:
                col_name = f'return_{period}'
                # Use numpy for ranking (much faster than pandas rank)
                values = df[col_name].values
                valid_mask = ~np.isnan(values)
                
                if valid_mask.sum() > 0:
                    valid_values = values[valid_mask]
                    sorted_indices = np.argsort(valid_values)
                    ranks = np.empty_like(sorted_indices)
                    ranks[sorted_indices] = np.arange(len(valid_values))
                    percentiles = (ranks / (len(valid_values) - 1)) * 100 if len(valid_values) > 1 else np.array([50])
                    
                    period_ratings = np.full(len(df), np.nan)
                    period_ratings[valid_mask] = np.clip(np.round(percentiles), 1, 99)
                    # Convert properly
                    df[f'rank_{period}'] = pd.Series(period_ratings).fillna(-1).astype(int).replace({-1: None})
            
            # 4. Calculate RS Rating
            rs_raw_values = df['rs_raw'].values
            valid_mask = ~np.isnan(rs_raw_values)
            
            if valid_mask.sum() > 0:
                valid_rs = rs_raw_values[valid_mask]
                sorted_indices = np.argsort(valid_rs)
                ranks = np.empty_like(sorted_indices)
                ranks[sorted_indices] = np.arange(len(valid_rs))
                percentiles = (ranks / (len(valid_rs) - 1)) * 100 if len(valid_rs) > 1 else np.array([50])
                
                rs_ratings = np.full(len(df), np.nan)
                rs_ratings[valid_mask] = np.clip(np.round(percentiles), 1, 99)
                # Convert properly
                df['rs_rating'] = pd.Series(rs_ratings).fillna(-1).astype(int).replace({-1: None})
            
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
        """Bulk save using temp table"""
        with self.engine.begin() as conn:
            # Create temp table
            conn.execute(text("""
                CREATE TEMP TABLE temp_rs_batch (
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
                    industry_group VARCHAR(255)
                ) ON COMMIT DROP
            """))
        
        # Save to temp table
        df.to_sql('temp_rs_batch', self.engine, if_exists='append', index=False, method='multi')
        
        # Bulk insert/update with DISTINCT to avoid duplicate error
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO rs_daily 
                (symbol, date, rs_rating, rs_raw, return_3m, return_6m, return_9m, return_12m,
                 rank_3m, rank_6m, rank_9m, rank_12m, company_name, industry_group)
                SELECT DISTINCT ON (symbol, date)
                    symbol, date, rs_rating, rs_raw, return_3m, return_6m, return_9m, return_12m,
                    rank_3m, rank_6m, rank_9m, rank_12m, company_name, industry_group
                FROM temp_rs_batch
                ORDER BY symbol, date
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
            """))
        
        return len(df)
    
    def _save_simple(self, df):
        """Simple save as fallback"""
        if len(df) == 0:
            return 0
        
        saved_count = 0
        batch_size = 50
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            
            try:
                stmt = text("""
                    INSERT INTO rs_daily 
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
                """)
                
                with self.engine.begin() as conn:
                    conn.execute(stmt, batch.to_dict('records'))
                
                saved_count += len(batch)
                logger.debug(f"✅ Saved batch {i//batch_size + 1}: {len(batch)} records")
                
            except Exception as e:
                logger.error(f"❌ Failed to save batch {i//batch_size + 1}: {e}")
                continue
        
        return saved_count
    
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

def main():
    """Main function"""
    
    DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"
    
    print("="*80)
    print("🚀 **RS Calculator - ULTRA FAST VERSION WITH ERROR HANDLING**")
    print("="*80)
    
    calculator = RSCalculatorUltraFast(DB_URL)
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--auto', '--resume']:
            print("\n🚀 Continuing from where we left off...")
            calculator.continue_from_checkpoint()
            return
    
    calculator.show_progress()
    
    print("\n📋 **Choose Action:**")
    print("1. ⚡ **Start Ultra-Fast Calculation** (Recommended)")
    print("2. 📍 Continue from checkpoint")
    print("3. 🗑️  Clean and start over")
    print("="*80)
    
    choice = input("\nChoose (1-3) [1]: ").strip() or "1"
    
    if choice == "1":
        print("\n⚡ Starting ultra-fast calculation...")
        calculator.calculate_historical_ultrafast(batch_size=200)
    
    elif choice == "2":
        print("\n📍 Continuing from last checkpoint...")
        calculator.continue_from_checkpoint()
    
    elif choice == "3":
        confirm = input("\n⚠️  **Warning**: All RS data will be deleted! Continue? (y/n): ").lower()
        if confirm == 'y':
            try:
                with calculator.engine.begin() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS rs_daily CASCADE"))
                    conn.execute(text("DROP TABLE IF EXISTS calculation_checkpoint CASCADE"))
                    conn.commit()
                print("✅ Cleaned and ready for fresh start")
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("❌ Cancelled")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  **User Stopped**")
        print("💾 Progress saved")
        print("🔄 Run --resume to continue")
    except Exception as e:
        print(f"\n\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()