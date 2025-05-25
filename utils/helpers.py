from datetime import datetime, timezone

def get_current_datetime_utc() -> str:
    """Get current date and time in UTC format YYYY-MM-DD HH:MM:SS"""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S")