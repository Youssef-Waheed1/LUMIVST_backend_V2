# check_dates.py
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta

def check_date_range():
    """Check data for dates from July 17 to July 21, 2014"""
    
    print("=" * 80)
    print("📊 **DATA VERIFICATION: 2014-07-17 to 2014-07-21**")
    print("=" * 80)
    
    # Database connection
    engine = create_engine(
        'postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn'
    )
    
    # Dates to check
    dates_to_check = [
        '2017-08-26',  # Last calculated date
        '2017-08-05',  # Sunday (might be holiday)
        '2017-08-27'  # Monday (had error)

    ]
    
    with engine.connect() as conn:
        for date_str in dates_to_check:
            print(f"\n🔍 **{date_str}**")
            print("-" * 40)
            
            # 1. Check if date exists in rs_daily
            exists_rs = conn.execute(
                text('SELECT EXISTS(SELECT 1 FROM rs_daily WHERE date = :date)'),
                {'date': date_str}
            ).scalar()
            
            # 2. Check if date exists in prices
            exists_prices = conn.execute(
                text('SELECT EXISTS(SELECT 1 FROM prices WHERE date = :date)'),
                {'date': date_str}
            ).scalar()
            
            # 3. Check if date is weekend
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            is_weekend = date_obj.weekday() >= 5  # 5=Saturday, 6=Sunday
            
            print(f"   📅 In prices table: {'✅ YES' if exists_prices else '❌ NO'}")
            print(f"   📊 In rs_daily table: {'✅ YES' if exists_rs else '❌ NO'}")
            print(f"   🗓️  Day of week: {date_obj.strftime('%A')}")
            print(f"   🏖️  Weekend/Holiday: {'✅ YES' if is_weekend else '❌ NO'}")
            
            if not exists_prices:
                print(f"   ⚠️  No price data - likely market holiday")
                continue
            
            if exists_rs:
                # Get detailed data
                # Count
                count = conn.execute(
                    text('SELECT COUNT(*) FROM rs_daily WHERE date = :date'),
                    {'date': date_str}
                ).scalar()
                
                # Check completeness
                completeness = conn.execute(text('''
                    SELECT 
                        COUNT(*) as total,
                        COUNT(rs_rating) as with_rating,
                        COUNT(rs_raw) as with_raw,
                        COUNT(return_3m) as with_3m,
                        COUNT(return_6m) as with_6m
                    FROM rs_daily 
                    WHERE date = :date
                '''), {'date': date_str}).fetchone()
                
                print(f"   📈 Stocks in rs_daily: {count}")
                
                if completeness[0] > 0:
                    print(f"   ✅ RS Rating: {completeness[1]}/{completeness[0]}")
                    print(f"   ✅ RS Raw: {completeness[2]}/{completeness[0]}")
                    print(f"   ✅ 3m Return: {completeness[3]}/{completeness[0]}")
                    print(f"   ✅ 6m Return: {completeness[4]}/{completeness[0]}")
                    
                    # Get top 3 stocks
                    top_stocks = conn.execute(text('''
                        SELECT symbol, rs_rating, rs_raw, company_name
                        FROM rs_daily 
                        WHERE date = :date 
                        ORDER BY rs_rating DESC 
                        LIMIT 3
                    '''), {'date': date_str}).fetchall()
                    
                    if top_stocks:
                        print(f"   🏆 Top 3 stocks:")
                        for i, (symbol, rating, rs_raw, company) in enumerate(top_stocks, 1):
                            print(f"      {i}. {symbol}: RS={rating}, Raw={rs_raw:.4f}")
                else:
                    print(f"   ⚠️  No complete data found")
            
            else:
                print(f"   ⚠️  Date exists in prices but NOT in rs_daily")
                print(f"   🔧 Should be calculated by the script")
                
                # Check how many stocks in prices for this date
                prices_count = conn.execute(
                    text('SELECT COUNT(DISTINCT symbol) FROM prices WHERE date = :date'),
                    {'date': date_str}
                ).scalar()
                
                print(f"   📊 Stocks in prices table: {prices_count}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 **SUMMARY**")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Get all dates in July 2014
        july_dates = conn.execute(text('''
            SELECT DISTINCT date
            FROM prices 
            WHERE date >= '2014-07-01' AND date <= '2014-07-31'
            ORDER BY date
        ''')).fetchall()
        
        july_dates_list = [d[0].strftime('%Y-%m-%d') for d in july_dates]
        
        # Get calculated dates in July
        calculated_dates = conn.execute(text('''
            SELECT DISTINCT date
            FROM rs_daily 
            WHERE date >= '2014-07-01' AND date <= '2014-07-31'
            ORDER BY date
        ''')).fetchall()
        
        calculated_dates_list = [d[0].strftime('%Y-%m-%d') for d in calculated_dates]
        
        print(f"\n📅 July 2014 Market Days: {len(july_dates_list)}")
        print(f"📊 July 2014 Calculated Days: {len(calculated_dates_list)}")
        
        missing = [d for d in july_dates_list if d not in calculated_dates_list]
        
        if missing:
            print(f"❌ Missing calculations: {len(missing)} days")
            print(f"   Dates: {', '.join(missing[:10])}" + ("..." if len(missing) > 10 else ""))
        else:
            print("✅ All July 2014 days are calculated!")
        
        # Last 5 calculated dates
        print(f"\n📈 Last 5 calculated dates:")
        last_dates = conn.execute(text('''
            SELECT date, COUNT(*) as stocks
            FROM rs_daily 
            WHERE rs_rating IS NOT NULL
            GROUP BY date
            ORDER BY date DESC
            LIMIT 5
        ''')).fetchall()
        
        for date_obj, count in last_dates:
            print(f"   {date_obj}: {count} stocks")

def verify_duplicate_issue():
    """Check for duplicate data issue"""
    
    print("\n" + "=" * 80)
    print("🔧 **DUPLICATE DATA CHECK**")
    print("=" * 80)
    
    engine = create_engine(
        'postgresql://youssef:UtnuCIs7PL3879r7R4jjIHi5FBqoHpKy@dpg-d4k8djidbo4c73cqncl0-a.oregon-postgres.render.com/financialdb_bvyn'
    )
    
    with engine.connect() as conn:
        # Check for duplicates in recent dates
        duplicates = conn.execute(text('''
            SELECT date, COUNT(*) as total_days
            FROM (
                SELECT date, COUNT(*) as cnt
                FROM rs_daily 
                WHERE date >= '2014-07-15'
                GROUP BY date, symbol
                HAVING COUNT(*) > 1
            ) AS dup_counts
            GROUP BY date
            ORDER BY date
        ''')).fetchall()
        
        if duplicates:
            print("⚠️  Found dates with duplicate symbol entries:")
            for date_obj, count in duplicates:
                print(f"   {date_obj}: {count} duplicate symbols")
        else:
            print("✅ No duplicate symbol entries found")
        
        # Check specific problematic dates
        problem_dates = ['2014-07-20', '2014-07-21']
        
        for date_str in problem_dates:
            print(f"\n🔍 Checking {date_str} for issues:")
            
            # Check if any data exists
            has_data = conn.execute(
                text('SELECT EXISTS(SELECT 1 FROM rs_daily WHERE date = :date)'),
                {'date': date_str}
            ).scalar()
            
            if has_data:
                # Check data quality
                quality = conn.execute(text('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN rs_rating IS NULL THEN 1 ELSE 0 END) as null_rating,
                        SUM(CASE WHEN rs_raw IS NULL THEN 1 ELSE 0 END) as null_raw
                    FROM rs_daily 
                    WHERE date = :date
                '''), {'date': date_str}).fetchone()
                
                print(f"   Total rows: {quality[0]}")
                print(f"   Null RS ratings: {quality[1]}")
                print(f"   Null RS raw: {quality[2]}")
                
                if quality[1] > 0 or quality[2] > 0:
                    print(f"   ⚠️  Incomplete data found")
            else:
                print(f"   ❌ No data in rs_daily")

if __name__ == "__main__":
    check_date_range()
    verify_duplicate_issue()