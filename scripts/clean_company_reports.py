import sys
import os

# Add parent directory to path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import argparse

# Load env variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def clean_company_reports(symbol, excel_only=False, force=False, language=None):
    target_str = f"{language.upper() if language else 'ALL'} reports" 
    if excel_only: target_str += " (EXCEL only)"
    
    print(f"⚠️  WARNING: You are about to DELETE {target_str} for symbol '{symbol}'.")
    print("This includes Database records AND Cloudflare R2 files.")
    
    if not force:
        confirm = input("Are you sure? (type 'yes' to confirm): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return

    # 1. Clean DB
    if DATABASE_URL:
        # Import models locally to avoid circular imports if any
        try:
            # We need to import SessionLocal (assuming it's available)
            # Adjust import based on your project structure
            from app.core.database import SessionLocal
            from app.models.official_filings import CompanyOfficialFiling, FileType, FilingLanguage
            
            db = SessionLocal()
            try:
                query = db.query(CompanyOfficialFiling).filter(CompanyOfficialFiling.company_symbol == symbol)
                
                if language:
                    lang_enum = FilingLanguage.AR if language.lower() == 'ar' else FilingLanguage.EN
                    query = query.filter(CompanyOfficialFiling.language == lang_enum)
                
                if excel_only:
                    query = query.filter(CompanyOfficialFiling.file_type == FileType.EXCEL)
                
                deleted_count = query.delete(synchronize_session=False)
                db.commit()
                print(f"✅ Deleted {deleted_count} records from Database.")
            except Exception as e:
                db.rollback()
                print(f"❌ Database Delete Error: {e}")
            finally:
                db.close()
        except ImportError:
            print("❌ Could not import app modules. Make sure you are running from backend root.")
    else:
        print("❌ DATABASE_URL not set.")

    # 2. Clean R2
    if S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
        try:
            import boto3
            s3 = boto3.resource('s3',
                endpoint_url=S3_ENDPOINT,
                aws_access_key_id=S3_ACCESS_KEY,
                aws_secret_access_key=S3_SECRET_KEY
            )
            bucket = s3.Bucket(S3_BUCKET_NAME)
            
            # Prefix structure: symbol/year/lang/filename
            # If lang is specified, we must iterate years or just scan all and filter by key structure
            # Key format from ingest: f"{symbol}/{year}/{language}/{filename}.{ext}"
            
            print(f"⏳ Scanning files in bucket '{S3_BUCKET_NAME}' for deletion...")
            
            objects_to_delete = []
            
            # We list all objects for symbol to be safe and filter in python
            # (S3 doesn't support wildcard in prefix for middle part easily)
            for obj in bucket.objects.filter(Prefix=f"{symbol}/"):
                key = obj.key
                # Check Language
                if language:
                    # Expected: 8313/2024/ar/file.pdf
                    parts = key.split('/')
                    if len(parts) >= 3:
                        file_lang = parts[2] # 0=sym, 1=year, 2=lang
                        if file_lang != language:
                            continue
                
                # Check Excel
                if excel_only:
                    if not (key.endswith('.xls') or key.endswith('.xlsx')):
                        continue
                
                objects_to_delete.append({'Key': key})

            if objects_to_delete:
                # Delete in batches of 1000 (S3 limit)
                for i in range(0, len(objects_to_delete), 1000):
                    batch = objects_to_delete[i:i+1000]
                    bucket.delete_objects(Delete={'Objects': batch})
                print(f"✅ Deleted {len(objects_to_delete)} files from R2.")
            else:
                print("ℹ️  No matching files found in R2.")
            
        except Exception as e:
            print(f"❌ S3/R2 Error: {e}")
    else:
        print("❌ S3 Credentials not set.")

    print("\nCleanup Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Clean company reports from DB and R2')
    parser.add_argument('symbol', type=str, help='Company Symbol')
    parser.add_argument('--excel-only', action='store_true', help='Delete only Excel files and records')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--lang', type=str, choices=['en', 'ar'], default='en', help='Language to delete: en or ar (default: en)')
    parser.add_argument('--all-langs', action='store_true', help='Delete ALL languages (en + ar). USE WITH CAUTION.')
    
    args = parser.parse_args()

    # --all-langs overrides --lang to delete everything
    lang_to_delete = None if args.all_langs else args.lang

    clean_company_reports(args.symbol, args.excel_only, args.force, lang_to_delete)

