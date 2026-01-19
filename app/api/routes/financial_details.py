from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import boto3
import json
import logging
import os
from app.core.config import settings

router = APIRouter()

# S3 Configuration (Load from Env or Settings)
# Ideally, this should be in a service, but for direct proxying we can init here or re-use existing
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET_NAME = "lumivst-reports" # Ensure this matches your bucket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/{symbol}/xbrl", response_model=Dict[str, Any])
async def get_company_xbrl_data(symbol: str):
    """
    Fetches the detailed XBRL financial data (JSON) from R2 storage.
    This JSON contains all parsed metrics from Excel files.
    """
    try:
        session = boto3.session.Session()
        s3 = session.client(
            service_name='s3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
        )
        
        key = f"{symbol}/financials.json"
        
        # Check if exists (Head Object) - Optional, get_object throws error if not found
        try:
            response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            return data
            
        except s3.exceptions.NoSuchKey:
             raise HTTPException(status_code=404, detail="Financial data not found for this company.")
        except Exception as e:
             logger.error(f"S3 Error for {symbol}: {e}")
             raise HTTPException(status_code=500, detail=f"Error retrieving data: {str(e)}")

    except Exception as e:
        logger.error(f"Critical Error in XBRL endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
