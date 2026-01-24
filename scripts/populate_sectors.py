import pandas as pd
import logging
from sqlalchemy import create_engine, text
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_sectors_from_csv():
    csv_path = Path(__file__).resolve().parent.parent.parent / "new.csv"
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return

    logger.info(f"Reading mapping from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Check columns
    required_cols = ['Symbol', 'Industry Group', 'Sector', 'Industry', 'Sub-Industry']
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Missing column {col} in CSV")
            return

    engine = create_engine(str(settings.DATABASE_URL))
    
    with engine.connect() as conn:
        logger.info("Updating existing records in the prices table...")
        
        updated_count = 0
        for _, row in df.iterrows():
            symbol = str(row['Symbol'])
            industry_group = row['Industry Group']
            sector = row['Sector']
            industry = row['Industry']
            sub_industry = row['Sub-Industry']
            
            query = text("""
                UPDATE prices 
                SET industry_group = :ig, 
                    sector = :s, 
                    industry = :i, 
                    sub_industry = :si
                WHERE symbol = :symbol
            """)
            
            result = conn.execute(query, {
                "ig": industry_group,
                "s": sector,
                "i": industry,
                "si": sub_industry,
                "symbol": symbol
            })
            updated_count += result.rowcount
            
        conn.commit()
    
    logger.info(f"Done! Updated {updated_count} price entries across all dates.")

if __name__ == "__main__":
    update_sectors_from_csv()
