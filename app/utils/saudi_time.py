"""
Utility module for handling Saudi Arabia timezone conversions (Asia/Riyadh - UTC+3)
"""

from datetime import datetime
from zoneinfo import ZoneInfo

SAUDI_TIMEZONE = ZoneInfo("Asia/Riyadh")

def get_saudi_now() -> datetime:
    """Get current datetime in Saudi Arabia timezone"""
    return datetime.now(SAUDI_TIMEZONE)

def convert_to_saudi_time(dt: datetime) -> datetime:
    """
    Convert any datetime to Saudi Arabia timezone
    
    Args:
        dt: datetime object (timezone-aware or naive)
    
    Returns:
        datetime object in Asia/Riyadh timezone
    """
    if dt is None:
        return None
    
    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    
    return dt.astimezone(SAUDI_TIMEZONE)

def utc_timestamp_to_saudi(timestamp: int) -> dict:
    """
    Convert UTC timestamp to Saudi time
    
    Args:
        timestamp: Unix timestamp in seconds (UTC)
    
    Returns:
        dict with both datetime string and timestamp in Saudi time
    """
    if not timestamp:
        return {
            "datetime": None,
            "timestamp": None
        }
    
    # Convert timestamp to datetime (UTC)
    utc_dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC"))
    
    # Convert to Saudi time
    saudi_dt = utc_dt.astimezone(SAUDI_TIMEZONE)
    
    return {
        "datetime": saudi_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": int(saudi_dt.timestamp())
    }

def format_saudi_datetime(dt: datetime = None) -> str:
    """
    Format datetime in Saudi timezone as string
    
    Args:
        dt: datetime object (if None, uses current time)
    
    Returns:
        Formatted string: "YYYY-MM-DD HH:MM:SS"
    """
    if dt is None:
        dt = get_saudi_now()
    else:
        dt = convert_to_saudi_time(dt)
    
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_saudi_metadata() -> dict:
    """
    Get complete metadata object with Saudi time information
    
    Returns:
        dict with exchange info and current Saudi time
    """
    now = get_saudi_now()
    
    return {
        "exchange": "TADAWUL",
        "mic_code": "XSAU",
        "currency": "SAR",
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": int(now.timestamp()),
        "timezone": "Asia/Riyadh (UTC+3)"
    }