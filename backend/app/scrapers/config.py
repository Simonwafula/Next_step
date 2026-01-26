# scrapers/config.py

import os
import yaml

# Determine path to YAML config (override via JOB_CONFIG env var)
_CONFIG_PATH = os.getenv(
    "JOB_CONFIG", os.path.join(os.path.dirname(__file__), "config.yaml")
)

# Load YAML configuration
with open(_CONFIG_PATH, "r") as cfg_file:
    _cfg = yaml.safe_load(cfg_file)

# Default settings (can be overridden via environment variables)
DB_PATH = os.getenv(
    "JOB_DB_PATH", _cfg.get("default", {}).get("db_path", "db/jobs.sqlite3")
)
TABLE_NAME = os.getenv(
    "JOB_TABLE", _cfg.get("default", {}).get("table_name", "jobs_data")
)
REQUESTS_PER_MINUTE = int(
    os.getenv("JOB_RPM", _cfg.get("default", {}).get("requests_per_minute", 60))
)

# Database type configuration
USE_POSTGRES = os.getenv("USE_POSTGRES", "true").lower() == "true"

# Site-specific configurations
SITES = _cfg.get("sites", {})


def get_site_cfg(name: str) -> dict:
    """
    Retrieve the configuration dict for a given site name.
    Raises KeyError if the site is not defined in config.yaml.
    """
    try:
        return SITES[name]
    except KeyError:
        raise KeyError(f"Site configuration '{name}' not found in config.yaml")
