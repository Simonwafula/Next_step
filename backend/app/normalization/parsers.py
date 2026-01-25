import re
from datetime import datetime, timedelta

def parse_salary(text: str) -> tuple[float | None, float | None, str | None]:
    """
    Parses salary strings like "50,000 - 80,000 KES" or "Monthly: 100k".
    Returns (min, max, currency).
    """
    if not text:
        return (None, None, None)
        
    t = text.lower().replace(",", "")
    
    # Detect currency
    currency = "KES" # Default
    if "usd" in t or "$" in t:
        currency = "USD"
    elif "eur" in t or "€" in t:
        currency = "EUR"
        
    # Find numbers
    # Handle "100k" -> 100000
    t = re.sub(r"(\d+)k", lambda m: str(int(m.group(1)) * 1000), t)
    
    nums = re.findall(r"\d+(?:\.\d+)?", t)
    nums = [float(n) for n in nums]
    
    if len(nums) >= 2:
        return (min(nums), max(nums), currency)
    elif len(nums) == 1:
        return (nums[0], nums[0], currency)
        
    return (None, None, currency)

def parse_date(text: str) -> datetime | None:
    """
    Standardizes various date formats found in job posts.
    Handles "2 days ago", "1 hour ago", "Dec 20th", etc.
    """
    if not text:
        return None
        
    t = text.lower().strip()
    now = datetime.utcnow()
    
    # Relative dates
    if "today" in t:
        return now
    if "yesterday" in t:
        return now - timedelta(days=1)
        
    relative_match = re.search(r"(\d+)\s+(day|hour|week|month)s?\s+ago", t)
    if relative_match:
        val = int(relative_match.group(1))
        unit = relative_match.group(2)
        if "day" in unit:
            return now - timedelta(days=val)
        if "hour" in unit:
            return now - timedelta(hours=val)
        if "week" in unit:
            return now - timedelta(weeks=val)
        if "month" in unit:
            return now - timedelta(days=val * 30) # Approx
            
    # Try standard parsing
    try:
        # Remove suffixes like 1st, 2nd, 3rd, 4th
        t_clean = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", t)
        # Try a few common formats
        for fmt in ["%b %d, %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
            try:
                return datetime.strptime(t_clean, fmt)
            except ValueError:
                continue
    except Exception:
        pass
        
    return None
