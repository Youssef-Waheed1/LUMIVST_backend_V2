import sys
sys.path.append('.')
from app.core.database import SessionLocal
from sqlalchemy import text
import pandas as pd

db = SessionLocal()

# Check data availability
queries = [
    ('Total Prices', 'SELECT COUNT(*) as cnt FROM prices'),
    ('Date Range', 'SELECT MIN(date), MAX(date) FROM prices'),
    ('With Industry Group', "SELECT COUNT(*) FROM prices WHERE industry_group IS NOT NULL AND TRIM(industry_group) != ''"),
    ('With Market Cap > 0', 'SELECT COUNT(*) FROM prices WHERE market_cap > 0'),
    ('With All Fields', "SELECT COUNT(*) FROM prices WHERE industry_group IS NOT NULL AND TRIM(industry_group) != '' AND market_cap > 0 AND close > 0"),
    ('Sample Data', 'SELECT symbol, date, close, market_cap, industry_group FROM prices ORDER BY date DESC LIMIT 5'),
]

for name, query in queries:
    try:
        with db.bind.connect() as conn:
            result = pd.read_sql(text(query), conn)
            print(f'{name}:')
            print(result)
            print()
    except Exception as e:
        print(f'{name}: ERROR - {e}')

db.close()
