import sys
import os
import boto3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def clean_company_reports(symbol):
    print(f"⚠️  WARNING: You are about to DELETE ALL reports for symbol '{symbol}'.")
    print("This includes Database records AND Cloudflare R2 files.")
    confirm = input("Are you sure? (type 'yes' to confirm): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled.")
        return

    # 1. Cleaner DB
    if DATABASE_URL:
        try:
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                # Delete from valid table name (check your models)
                # Assuming table is 'company_official_filings' based on schema
                query = text("DELETE FROM company_official_filings WHERE company_symbol = :symbol")
                result = conn.execute(query, {"symbol": symbol})
                conn.commit()
                print(f"✅ Deleted {result.rowcount} records from Database.")
        except Exception as e:
            print(f"❌ Database Error: {e}")
    else:
        print("❌ DATABASE_URL not found.")

    # 2. Clean R2
    if S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
        try:
            s3 = boto3.resource('s3',
                endpoint_url=S3_ENDPOINT,
                aws_access_key_id=S3_ACCESS_KEY,
                aws_secret_access_key=S3_SECRET_KEY
            )
            bucket = s3.Bucket(S3_BUCKET_NAME)
            
            # Delete all objects with prefix {symbol}/
            print(f"⏳ Deleting files from R2 bucket '{S3_BUCKET_NAME}' with prefix '{symbol}/'...")
            bucket.objects.filter(Prefix=f"{symbol}/").delete()
            print(f"✅ Deleted files from Cloudflare R2.")
            
        except Exception as e:
            print(f"❌ S3/R2 Error: {e}")
    else:
        print("❌ S3 Credentials not found.")

    print("\nCleanup Complete. You can now re-scrape freshly.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/clean_company_reports.py <SYMBOL>")
    else:
        clean_company_reports(sys.argv[1])
