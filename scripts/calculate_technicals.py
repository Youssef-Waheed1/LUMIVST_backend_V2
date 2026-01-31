import sys
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging

# إضافة المسار للمجلد الرئيسي للوصول للإعدادات
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.config import settings

# إعداد الـ Logging لمتابعة سير العملية
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalCalculator:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)

    def load_data(self):
        # سحب كل الأعمدة اللازمة للحسابات بما فيها الـ high والـ low
        query = """
        SELECT id, symbol, date, close, high, low, volume_traded
        FROM prices
        ORDER BY symbol, date
        """
        logger.info("⏳ جاري تحميل البيانات من قاعدة البيانات...")
        with self.engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        df['date'] = pd.to_datetime(df['date'])
        logger.info(f"✅ تم تحميل {len(df)} سجل.")
        return df

    def calculate(self, df):
        logger.info("📈 جاري حساب المؤشرات الفنية (القيم الكاملة)...")
        
        # ترتيب البيانات لضمان دقة العمليات الحسابية المتسلسلة
        df = df.sort_values(['symbol', 'date'])
        grouped = df.groupby('symbol')

        # 1. حساب قيم المتوسطات المتحركة (SMA) مباشرة
        # الحساب يعتمد على سعر الإغلاق (Close) لآخر X يوم
        for window in [10, 21, 50, 150, 200]:
            df[f'sma_{window}'] = grouped['close'].transform(lambda x: x.rolling(window=window).mean())

        # 2. حساب الـ 52 Week High من عمود الـ High (أعلى سعر وصل له السهم)
        df['fifty_two_week_high'] = grouped['high'].transform(lambda x: x.rolling(window=252).max())

        # 3. حساب الـ 52 Week Low من عمود الـ Low (أقل سعر وصل له السهم)
        df['fifty_two_week_low'] = grouped['low'].transform(lambda x: x.rolling(window=252).min())

        # 4. حساب متوسط حجم التداول لـ 50 يوم (Average Volume)
        df['average_volume_50'] = grouped['volume_traded'].transform(lambda x: x.rolling(window=50).mean())

        # 5. حساب التغير (Change) = سعر إغلاق اليوم - سعر إغلاق أمس
        logger.info("   ... حساب التغير (Change)")
        df['change'] = grouped['close'].transform(lambda x: x.diff())

        # 5. حساب النسب المئوية (للفلترة والعرض المتقدم)
        # نسبة ابتعاد السعر عن المتوسطات
        for window in [10, 21, 50, 150, 200]:
            col_sma = f'sma_{window}'
            df[f'price_vs_sma_{window}_percent'] = ((df['close'] - df[col_sma]) / df[col_sma].replace(0, np.nan)) * 100
        
        # نسبة الابتعاد عن القمة والقاع السنوي
        df['percent_off_52w_high'] = ((df['close'] - df['fifty_two_week_high'].replace(0, np.nan)) / df['fifty_two_week_high'].replace(0, np.nan)) * 100
        df['percent_off_52w_low'] = ((df['close'] - df['fifty_two_week_low'].replace(0, np.nan)) / df['fifty_two_week_low'].replace(0, np.nan)) * 100
        
        # نسبة تغير حجم التداول عن المتوسط
        df['vol_diff_50_percent'] = ((df['volume_traded'] - df['average_volume_50']) / df['average_volume_50'].replace(0, np.nan)) * 100

        # تنظيف البيانات وتقريبها
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        cols_to_round = [
            'sma_10', 'sma_21', 'sma_50', 'sma_150', 'sma_200', 
            'fifty_two_week_high', 'fifty_two_week_low',
            'price_vs_sma_10_percent', 'price_vs_sma_21_percent', 'price_vs_sma_50_percent',
            'price_vs_sma_150_percent', 'price_vs_sma_200_percent',
            'percent_off_52w_high', 'percent_off_52w_low', 'vol_diff_50_percent'
        ]
        
        for col in cols_to_round:
            df[col] = df[col].round(2)

        return df

    def save_latest(self, df):
        """تحديث السجلات الأخيرة فقط في قاعدة البيانات لضمان السرعة"""
        logger.info("💾 جاري تحضير البيانات للحفظ...")
        
        latest_dates = df.groupby('symbol')['date'].max().reset_index()
        latest_data = pd.merge(df, latest_dates, on=['symbol', 'date'])
        
        logger.info(f"🚀 جاري تحديث {len(latest_data)} سهم...")
        
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                for idx, row in latest_data.iterrows():
                    update_stmt = text("""
                        UPDATE prices
                        SET change = :change,
                            price_minus_sma_10 = :p10,
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
                        'change': round(row['change'], 2) if pd.notnull(row['change']) else None,
                        # لاحظ: الأعمدة المسماة price_minus_sma في الداتابيز ستخزن الآن قيمة الـ SMA نفسه بناءً على طلبك
                        'p10': row['sma_10'] if pd.notnull(row['sma_10']) else None,
                        'p21': row['sma_21'] if pd.notnull(row['sma_21']) else None,
                        'p50': row['sma_50'] if pd.notnull(row['sma_50']) else None,
                        'p150': row['sma_150'] if pd.notnull(row['sma_150']) else None,
                        'p200': row['sma_200'] if pd.notnull(row['sma_200']) else None,
                        'h52': row['fifty_two_week_high'] if pd.notnull(row['fifty_two_week_high']) else None,
                        'l52': row['fifty_two_week_low'] if pd.notnull(row['fifty_two_week_low']) else None,
                        'avg_vol': int(row['average_volume_50']) if pd.notnull(row['average_volume_50']) else 0,
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
                logger.info("✅ تم تحديث جميع المؤشرات بنجاح.")
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ خطأ أثناء التحديث: {e}")
                raise

if __name__ == "__main__":
    calc = TechnicalCalculator(str(settings.DATABASE_URL))
    df = calc.load_data()
    df_calc = calc.calculate(df)
    calc.save_latest(df_calc)