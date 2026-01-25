import re

# Common company suffixes to strip for better matching
COMPANY_SUFFIXES = [
    " ltd", " limited", " llc", " inc", " incorporated", 
    " pvt", " private", " group", " corp", " corporation"
]

def normalize_company_name(raw: str) -> str:
    """
    Standardizes company names by:
    1. Lowercasing
    2. Stripping common suffixes
    3. Trimming whitespace
    """
    if not raw:
        return ""
    
    # Lowercase and strip whitespace
    name = raw.lower().strip()
    
    # Remove common suffixes
    for suffix in COMPANY_SUFFIXES:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
            break
            
    # Remove any trailing " & co", " and co"
    name = re.sub(r"\s+(and|&)\s+co\.?$", "", name)
    
    # Handle known aliases (can be expanded)
    ALIASES = {
        "kcb": "kcb bank",
        "equity": "equity bank",
        "safari com": "safaricom",
        "co-operative bank": "co-op bank",
    }
    
    if name in ALIASES:
        name = ALIASES[name]
        
    return name.title() # Return title case for cleaner storage
