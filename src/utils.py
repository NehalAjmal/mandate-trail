def format_inr(paise: int) -> str:
    """Format paise amount to INR string."""
    return f"₹{paise/100:,.2f}"

def format_ts(ts: int) -> str:
    """Format Unix timestamp to UTC string."""
    from datetime import datetime, timezone
    if not ts: return "None"
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
