import pandas as pd
import numpy as np
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine, text
from tqdm import tqdm
import time
import sys
import gc
import os
import psutil
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError
import socket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class RSCalculatorFast:
    def __init__(self, db_url):
        self.db_url = db_url
        self.engine = None
        self._reconnect()
        # إنشاء جدول checkpoint عند الإنشاء
        self._create_checkpoint_table()
    
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
        """إنشاء جدول checkpoint إذا لم يكن موجوداً"""
        try:
            self._execute_with_retry("""
                CREATE TABLE IF NOT EXISTS calculation_checkpoint (
                    id SERIAL PRIMARY KEY,
                    last_date DATE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.debug("✅ Checkpoint table created/verified")
        except Exception as e:
            logger.warning(f"⚠️  Could not create checkpoint table: {e}")
    
    def check_memory(self):
        """مراقبة استخدام الذاكرة"""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            return memory_mb
        except Exception:
            return 0
    
    def show_progress(self):
        """Show current calculation progress"""
        try:
            # الحصول على إجمالي الأيام من 2003
            result = self._execute_with_retry("""
                SELECT COUNT(DISTINCT date) 
                FROM prices 
                WHERE date >= '2003-01-01'
            """)
            total_days = result.scalar() or 0
            
            # الحصول على الأيام المحسوبة
            result = self._execute_with_retry("""
                SELECT COUNT(DISTINCT date) 
                FROM rs_daily 
                WHERE rs_rating IS NOT NULL
            """)
            calculated_days = result.scalar() or 0
            
            # الحصول على إجمالي تقييمات RS
            result = self._execute_with_retry("""
                SELECT COUNT(*) 
                FROM rs_daily 
                WHERE rs_rating IS NOT NULL
            """)
            total_ratings = result.scalar() or 0
            
            # آخر تاريخ محسوب
            result = self._execute_with_retry("""
                SELECT MAX(date) 
                FROM rs_daily 
                WHERE rs_rating IS NOT NULL
            """)
            latest_date = result.scalar()
            
            # آخر checkpoint
            try:
                result = self._execute_with_retry("SELECT MAX(last_date) FROM calculation_checkpoint")
                last_checkpoint = result.scalar()
            except:
                last_checkpoint = None
            
            print(f"\n📊 **Current Progress Report:**")
            print(f"   📅 Total days (from 2003): {total_days:,}")
            print(f"   ✅ Days calculated: {calculated_days:,}")
            
            if total_days > 0:
                completion = (calculated_days / total_days) * 100
                print(f"   📈 Completion: {completion:.1f}%")
            
            print(f"   📊 Total RS ratings: {total_ratings:,}")
            
            if latest_date:
                print(f"   🕐 Latest calculated date: {latest_date}")
            
            if last_checkpoint:
                print(f"   📍 Last checkpoint: {last_checkpoint}")
            
            remaining = total_days - calculated_days
            if remaining > 0:
                print(f"   ⏳ Remaining days: {remaining:,}")
                print(f"   🚀 Estimated time: ~{remaining * 3.5 / 3600:.1f} hours")
            
            # عرض استخدام الذاكرة
            memory_usage = self.check_memory()
            print(f"   💾 Memory usage: {memory_usage:.1f} MB")
            
            return total_days, calculated_days
            
        except Exception as e:
            print(f"⚠️  Could not get progress: {e}")
            return 0, 0
    
    def save_checkpoint(self, last_date):
        """Save checkpoint for resume"""
        try:
            self._execute_with_retry("DELETE FROM calculation_checkpoint")
            self._execute_with_retry("""
                INSERT INTO calculation_checkpoint (last_date) 
                VALUES (:last_date)
            """, {'last_date': last_date})
            logger.info(f"📍 Checkpoint saved for date: {last_date}")
        except Exception as e:
            logger.warning(f"⚠️  Could not save checkpoint: {e}")
    
    def get_last_checkpoint(self):
        """Get last checkpoint date"""
        try:
            result = self._execute_with_retry("SELECT MAX(last_date) FROM calculation_checkpoint")
            return result.scalar()
        except Exception as e:
            logger.debug(f"ℹ️  Could not get checkpoint: {e}")
            return None
    
    def cleanup_table(self):
        """Clean old RS table and start fresh"""
        try:
            self._execute_with_retry("DROP TABLE IF EXISTS rs_daily CASCADE")
            self._execute_with_retry("DROP TABLE IF EXISTS calculation_checkpoint CASCADE")
            logger.info("🗑️  Cleaned rs_daily and checkpoint tables")
            self._create_checkpoint_table()
        except Exception as e:
            logger.warning(f"⚠️  Cannot clean table: {e}")
    
    def setup_table(self):
        """Create the main RS Daily table with ALL columns"""
        
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
                has_rating BOOLEAN GENERATED ALWAYS AS (rs_rating IS NOT NULL) STORED,
                UNIQUE(symbol, date)
            )
        """)
        
        # إنشاء indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_rs_daily_symbol_date ON rs_daily(symbol, date)",
            "CREATE INDEX IF NOT EXISTS idx_rs_daily_date_rating ON rs_daily(date, rs_rating DESC)",
            "CREATE INDEX IF NOT EXISTS idx_rs_daily_rating_filter ON rs_daily(date) WHERE has_rating = TRUE",
            "CREATE INDEX IF NOT EXISTS idx_rs_daily_date_symbol ON rs_daily(date, symbol)"
        ]
        
        for idx_sql in indexes:
            try:
                self._execute_with_retry(idx_sql)
            except Exception as e:
                logger.warning(f"⚠️  Cannot create index: {e}")
                continue
        
        logger.info("✅ Created/updated table with required optimizations")
    
    def calculate_returns_with_nearest_date(self, df_group, current_date, current_price, months):
        """
        Calculate returns with actual date used
        """
        target_date = current_date - relativedelta(months=months)
        
        if isinstance(target_date, pd.Timestamp):
            target_date = target_date.to_pydatetime()
        
        past_data = df_group[df_group['date'] <= target_date]
        
        if len(past_data) == 0:
            return None, None, None
        
        past_row = past_data.iloc[-1]
        past_price = float(past_row['close'])
        actual_date_used = past_row['date']
        
        if past_price <= 0 or current_price <= 0:
            return None, None, None
        
        return_percent = (current_price - past_price) / past_price
        
        return return_percent, actual_date_used, past_price
    
    def calculate_daily_rs(self, target_date):
        """Calculate RS for a specific day"""
        
        logger.info(f"📅 Calculating RS for day {target_date}")
        
        # 1. Get current day data
        current_query = """
            SELECT 
                p.symbol,
                p.date,
                p.close,
                p.company_name,
                p.industry_group
            FROM prices p
            WHERE p.date = :target_date
            ORDER BY p.symbol
        """
        
        try:
            result = self._execute_with_retry(current_query, {'target_date': target_date})
            df_current = pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            logger.error(f"❌ Failed to get current data: {e}")
            return []
        
        if len(df_current) == 0:
            logger.warning(f"⚠️  No data for date: {target_date}")
            return []
        
        logger.info(f"🔢 Stocks count for day {target_date}: {len(df_current)}")
        
        # 2. Get historical data
        symbols = df_current['symbol'].tolist()
        
        if not symbols:
            return []
        
        symbols_placeholders = ', '.join([f"'{s}'" for s in symbols])
        
        hist_query = f"""
            SELECT 
                symbol,
                date,
                close
            FROM prices 
            WHERE symbol IN ({symbols_placeholders})
                AND date <= :target_date 
                AND date >= :start_date
            ORDER BY symbol, date
        """
        
        start_date = pd.to_datetime(target_date) - relativedelta(months=13)
        
        try:
            result = self._execute_with_retry(hist_query, {
                'target_date': target_date, 
                'start_date': start_date
            })
            df_history = pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            logger.error(f"❌ Failed to get historical data: {e}")
            return []
        
        df_current['date'] = pd.to_datetime(df_current['date'])
        df_history['date'] = pd.to_datetime(df_history['date'])
        
        df_current['close'] = df_current['close'].astype(float)
        df_history['close'] = df_history['close'].astype(float)
        
        # 3. Process each stock
        results = []
        memory_before = self.check_memory()
        
        for _, row in tqdm(df_current.iterrows(), total=len(df_current), desc=f"Processing {target_date}"):
            try:
                symbol = row['symbol']
                current_date = row['date']
                current_price = row['close']
                
                hist_data = df_history[df_history['symbol'] == symbol].copy()
                
                if len(hist_data) < 10:
                    continue
                
                hist_data = hist_data.sort_values('date')
                hist_data.reset_index(drop=True, inplace=True)
                
                returns = {}
                
                for months in [3, 6, 9, 12]:
                    return_pct, actual_date, past_price = self.calculate_returns_with_nearest_date(
                        hist_data, current_date, current_price, months
                    )
                    returns[f'return_{months}m'] = return_pct
                
                has_complete_data = all(r is not None for r in returns.values())
                
                if has_complete_data:
                    rs_raw = (
                        returns['return_3m'] * 0.4 +
                        returns['return_6m'] * 0.2 +
                        returns['return_9m'] * 0.2 +
                        returns['return_12m'] * 0.2
                    )
                else:
                    rs_raw = None
                
                results.append({
                    'symbol': symbol,
                    'date': current_date,
                    'current_price': current_price,
                    **returns,
                    'rs_raw': rs_raw,
                    'company_name': row['company_name'],
                    'industry_group': row['industry_group'],
                    'has_complete_data': has_complete_data
                })
                
            except Exception as e:
                logger.error(f"Error in symbol {row.get('symbol', 'unknown')}: {e}")
                continue
        
        # 4. Calculate RS Rating
        complete_results = [r for r in results if r['has_complete_data']]
        
        if complete_results:
            df_complete = pd.DataFrame(complete_results)
            
            df_complete['rs_rating'] = (
                df_complete['rs_raw']
                .rank(pct=True, method='average')
                .mul(100)
                .round(0)
                .clip(upper=99)
                .astype(int)
            )
            
            for period in ['3m', '6m', '9m', '12m']:
                col = f'return_{period}'
                df_complete[f'rank_{period}'] = (
                    df_complete[col]
                    .rank(pct=True, method='average')
                    .mul(100)
                    .round(0)
                    .clip(upper=99)
                    .astype(int)
                )
            
            rating_dict = df_complete.set_index('symbol')[['rs_rating']].to_dict()['rs_rating']
            ranks_dict = {period: df_complete.set_index('symbol')[f'rank_{period}'].to_dict() 
                         for period in ['3m', '6m', '9m', '12m']}
            
            for r in complete_results:
                symbol = r['symbol']
                if symbol in rating_dict:
                    r['rs_rating'] = int(rating_dict[symbol])
                    for period in ['3m', '6m', '9m', '12m']:
                        r[f'rank_{period}'] = int(ranks_dict[period].get(symbol, 0))
        
        memory_after = self.check_memory()
        logger.info(f"✅ Calculated RS for {len(complete_results)} stocks out of {len(results)}")
        if memory_before > 0:
            logger.info(f"💾 Memory delta: {memory_after - memory_before:.1f} MB")
        
        return results
    
    def save_daily_results(self, results):
        """Save daily results to database"""
        
        if not results:
            return 0, 0
        
        complete_data = [r for r in results if r.get('has_complete_data', False)]
        
        if not complete_data:
            return 0, len(results)
        
        complete_records = []
        seen = set()
        
        for r in complete_data:
            date_str = r['date']
            if isinstance(date_str, (pd.Timestamp, datetime)):
                date_str = date_str.strftime('%Y-%m-%d')
            
            key = (r['symbol'], date_str)
            if key in seen:
                continue
            seen.add(key)
            
            complete_records.append({
                'symbol': r['symbol'], 
                'date': date_str,
                'rs_rating': r.get('rs_rating'), 
                'rs_raw': r.get('rs_raw'),
                'return_3m': r.get('return_3m'), 
                'return_6m': r.get('return_6m'),
                'return_9m': r.get('return_9m'), 
                'return_12m': r.get('return_12m'),
                'rank_3m': r.get('rank_3m'), 
                'rank_6m': r.get('rank_6m'),
                'rank_9m': r.get('rank_9m'), 
                'rank_12m': r.get('rank_12m'), 
                'company_name': r.get('company_name'), 
                'industry_group': r.get('industry_group')
            })
        
        if not complete_records:
            return 0, len(results)
        
        # استخدام الطريقة البسيطة لتجنب مشاكل الاتصال
        try:
            with self.engine.begin() as conn:
                # إنشاء جدول مؤقت
                conn.execute(text("""
                    CREATE TEMP TABLE temp_rs_data (
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
        except Exception as e:
            logger.warning(f"⚠️  Could not create temp table: {e}")
            return self._save_simple(complete_records)
        
        # إدخال البيانات في الجدول المؤقت
        try:
            df_to_save = pd.DataFrame(complete_records)
            df_to_save.to_sql('temp_rs_data', self.engine, if_exists='append', index=False)
        except Exception as e:
            logger.warning(f"⚠️  Could not insert into temp table: {e}")
            return self._save_simple(complete_records)
        
        # Bulk upsert
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO rs_daily 
                    (symbol, date, rs_rating, rs_raw, return_3m, return_6m, return_9m, return_12m,
                     rank_3m, rank_6m, rank_9m, rank_12m, company_name, industry_group)
                    SELECT DISTINCT ON (symbol, date) symbol, date::DATE, rs_rating, rs_raw, return_3m, return_6m, return_9m, return_12m,
                           rank_3m, rank_6m, rank_9m, rank_12m, company_name, industry_group
                    FROM temp_rs_data
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
        except Exception as e:
            logger.warning(f"⚠️  Bulk insert failed: {e}")
            return self._save_simple(complete_records)
        
        return len(complete_records), len(results)
    
    def _save_simple(self, complete_records):
        """طريقة بسيطة للحفظ كبديل"""
        if not complete_records:
            return 0, 0
        
        batch_size = 50  # دفعات أصغر
        saved_count = 0
        
        for i in range(0, len(complete_records), batch_size):
            batch = complete_records[i:i + batch_size]
            
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
                    conn.execute(stmt, batch)
                
                saved_count += len(batch)
                logger.debug(f"✅ Saved batch {i//batch_size + 1}: {len(batch)} records")
                
            except Exception as e:
                logger.error(f"❌ Failed to save batch {i//batch_size + 1}: {e}")
                continue
        
        return saved_count, 0
    
    def calculate_historical_fast(self, start_date='2003-01-01', batch_size=50):  # تقليل batch_size
        """Calculate historical RS with connection management"""
        
        total_days, calculated_days = self.show_progress()
        
        if calculated_days >= total_days and total_days > 0:
            logger.info("🎉 All days already calculated!")
            return
        
        logger.info(f"📊 Starting calculation from {start_date}")
        
        query = """
            SELECT DISTINCT p.date
            FROM prices p
            LEFT JOIN rs_daily r ON p.date = r.date AND r.rs_rating IS NOT NULL
            WHERE p.date >= :start_date 
            AND r.date IS NULL
            ORDER BY p.date
        """
        
        try:
            result = self._execute_with_retry(query, {'start_date': start_date})
            dates_df = pd.DataFrame(result.fetchall(), columns=['date'])
        except Exception as e:
            logger.error(f"❌ Failed to get dates: {e}")
            return
        
        all_dates = dates_df['date'].tolist()
        
        if not all_dates:
            logger.info("🎉 No dates to calculate!")
            return
        
        remaining_days = len(all_dates)
        logger.info(f"🔢 Remaining days to calculate: {remaining_days:,}")
        
        self.setup_table()
        
        start_time = time.time()
        total_complete = 0
        last_saved_date = None
        
        date_batches = [all_dates[i:i + batch_size] for i in range(0, remaining_days, batch_size)]
        
        for batch_num, date_batch in enumerate(date_batches, 1):
            batch_start_time = time.time()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📦 Batch {batch_num}/{len(date_batches)}")
            logger.info(f"📅 Days: {date_batch[0]} to {date_batch[-1]}")
            logger.info(f"🔢 Days in batch: {len(date_batch)}")
            logger.info(f"{'='*60}")
            
            batch_complete = 0
            
            for target_date in date_batch:
                try:
                    # اختبار الاتصال قبل كل يوم
                    if not self._test_connection():
                        logger.info("🔄 Reconnecting to database...")
                        self._reconnect()
                    
                    # حساب RS
                    results = self.calculate_daily_rs(target_date)
                    
                    # الحفظ
                    complete_count, _ = self.save_daily_results(results)
                    batch_complete += complete_count
                    
                    # حفظ checkpoint
                    last_saved_date = target_date
                    
                    # تنظيف الذاكرة
                    gc.collect()
                    
                    # إضافة تأخير صغير بين الأيام
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"❌ Error in {target_date}: {e}")
                    continue
            
            total_complete += batch_complete
            
            # حفظ checkpoint بعد كل batch
            if last_saved_date:
                try:
                    self.save_checkpoint(last_saved_date)
                except:
                    pass
            
            # تقرير Batch
            batch_elapsed = time.time() - batch_start_time
            if len(date_batch) > 0:
                avg_time_per_day = batch_elapsed / len(date_batch)
            else:
                avg_time_per_day = 0
            
            logger.info(f"\n📊 Batch {batch_num} Report:")
            logger.info(f"   ✅ Stocks calculated: {batch_complete:,}")
            logger.info(f"   ⏱️  Batch time: {batch_elapsed:.1f}s")
            logger.info(f"   🚀 Speed: {avg_time_per_day:.1f}s/day")
            
            remaining = len(date_batches) - batch_num
            if remaining > 0:
                est_remaining = remaining * (batch_elapsed / 60)
                logger.info(f"   ⏳ Remaining: ~{est_remaining:.1f} minutes")
            
            gc.collect()
        
        elapsed_minutes = (time.time() - start_time) / 60
        
        logger.info("\n" + "="*80)
        logger.info("🎉 Calculation complete!")
        logger.info("="*80)
        logger.info(f"📊 Statistics:")
        logger.info(f"   📅 Days calculated: {remaining_days}")
        logger.info(f"   ✅ Stocks with RS: {total_complete:,}")
        logger.info(f"   ⏱️  Total time: {elapsed_minutes:.1f} minutes")
        logger.info("="*80)
    
    def continue_from_checkpoint(self):
        """Continue calculation from last checkpoint"""
        last_checkpoint = self.get_last_checkpoint()
        
        if last_checkpoint:
            if isinstance(last_checkpoint, date):
                next_date = last_checkpoint
            else:
                next_date = pd.to_datetime(last_checkpoint).date()
            
            logger.info(f"📍 Resuming from checkpoint: {next_date}")
            next_date = next_date + pd.Timedelta(days=1)
            self.calculate_historical_fast(start_date=next_date.strftime('%Y-%m-%d'), batch_size=50)
        else:
            logger.info("ℹ️  No checkpoint found, getting last calculated date...")
            
            try:
                result = self._execute_with_retry("SELECT MAX(date) FROM rs_daily WHERE rs_rating IS NOT NULL")
                last_calculated = result.scalar()
            except:
                last_calculated = None
            
            if last_calculated:
                logger.info(f"📌 Last calculated date found: {last_calculated}")
                next_date = last_calculated + pd.Timedelta(days=1)
                self.calculate_historical_fast(start_date=next_date.strftime('%Y-%m-%d'), batch_size=50)
            else:
                logger.info("ℹ️  No data found, starting from beginning")
                self.calculate_historical_fast(batch_size=50)

def main():
    """Main function"""
    
    DB_URL = "postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn"
    
    print("="*80)
    print("🚀 **RS Calculator with CONNECTION MANAGEMENT**")
    print("="*80)
    
    calculator = RSCalculatorFast(DB_URL)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--auto':
            print("\n🚀 Auto-run: Continuing calculation where stopped...")
            calculator.continue_from_checkpoint()
            return
        elif sys.argv[1] == '--resume':
            print("\n🚀 Resuming from checkpoint...")
            calculator.continue_from_checkpoint()
            return
    
    calculator.show_progress()
    
    print("\n📋 **Choose action:**")
    print("1. ⚡ Continue calculation (with connection management)")
    print("2. 📍 Resume from checkpoint")
    print("3. 📊 Generate verification report")
    print("4. 🗑️  Clean and start fresh")
    print("5. 🛠️  Setup/Rebuild table")
    print("="*80)
    
    choice = input("\nChoose (1-5) [1]: ").strip() or "1"
    
    if choice == "1":
        print("\n⚡ Starting calculation...")
        
        batch_input = input("Batch size (days per batch) [50]: ").strip()
        batch_size = int(batch_input) if batch_input else 50
        
        start_input = input("Start date (YYYY-MM-DD) [2003-01-01]: ").strip()
        start_date = start_input if start_input else '2003-01-01'
        
        calculator.calculate_historical_fast(
            start_date=start_date,
            batch_size=batch_size
        )
    
    elif choice == "2":
        print("\n📍 Resuming from last checkpoint...")
        calculator.continue_from_checkpoint()
    
    elif choice == "3":
        date_input = input("Verification date (YYYY-MM-DD) or leave for latest: ").strip()
        
        if date_input:
            try:
                sample_date = pd.to_datetime(date_input).date()
            except:
                print("❌ Invalid date")
                sample_date = None
        else:
            sample_date = None
        
        # TODO: Add verification function
        print("Verification not implemented in this version")
    
    elif choice == "4":
        confirm = input("\n⚠️  **WARNING**: Will delete ALL RS data and checkpoints! Continue? (y/n): ").lower()
        if confirm == 'y':
            calculator.cleanup_table()
            calculator.setup_table()
            print("✅ Cleaned and ready for fresh start")
        else:
            print("❌ Cancelled")
    
    elif choice == "5":
        calculator.setup_table()
        print("✅ Table setup completed")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  **Process paused by user**")
        print("💾 Progress saved")
        print("🔄 Run with --resume to continue")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()