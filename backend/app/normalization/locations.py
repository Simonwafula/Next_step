import re

# Kenya-specific location mappings (main cities and counties)
KENYA_LOCATIONS = {
    "nairobi": ["nairobi", "westlands", "upper hill", "kilimani", "karen", "cbd", "embarkasi"],
    "mombasa": ["mombasa", "nyali", "likoni"],
    "kisumu": ["kisumu"],
    "nakuru": ["nakuru", "naivasha"],
    "eldoret": ["eldoret", "uasin gishu"],
    "thika": ["thika", "kiambu"],
    "machakos": ["machakos"],
    "remote": ["remote", "work from home", "anywhere"],
}

def normalize_location(raw: str) -> tuple[str, str, str]:
    """
    Normalizes location string to (city, region, country).
    Default country is Kenya if not specified.
    """
    if not raw:
        return (None, None, "Kenya")
        
    r = raw.lower().strip()
    
    # Fast match for known Kenya cities/regions
    for canon, patterns in KENYA_LOCATIONS.items():
        if any(p in r for p in patterns):
            if canon == "remote":
                return ("Remote", "Remote", "Kenya")
            return (canon.title(), canon.title(), "Kenya")
            
    # Fallback to basic cleaning
    cleaned = re.sub(r"[^a-z\s,]", "", r).strip()
    parts = [p.strip().title() for p in cleaned.split(",")]
    
    if len(parts) >= 2:
        return (parts[0], parts[1], "Kenya")
    elif len(parts) == 1:
        return (parts[0], parts[0], "Kenya")
        
    return (None, None, "Kenya")
