import os
from pathlib import Path
from zoneinfo import ZoneInfo

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUTS_DIR = DATA_DIR / "inputs"
OUTPUTS_DIR = DATA_DIR / "outputs"
SESSIONS_DIR = BASE_DIR / "sessions"

# Load .env variables manually to avoid extra package dependencies
env_path = BASE_DIR / ".env"
if env_path.exists():
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    val_str = val.strip()
                    if (val_str.startswith('"') and val_str.endswith('"')) or \
                       (val_str.startswith("'") and val_str.endswith("'")):
                        val_str = val_str[1:-1]
                    os.environ[key.strip()] = val_str
    except Exception as e:
        print(f"Warning: Failed to parse .env file: {e}")

def ensure_dirs():
    """Ensure that all required workspace directories exist."""
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Default File Paths
DEFAULT_INPUT_FILE = INPUTS_DIR / "users.csv"
DEFAULT_OUTPUT_FILE = OUTPUTS_DIR / "tweets.csv"
SESSION_FILE = SESSIONS_DIR / "twitter_session.json"

# Scraper Settings
TIMEZONE = ZoneInfo("Asia/Kolkata")
LOOKBACK_DAYS = int(os.environ.get("LOOKBACK_DAYS", "1"))
TIMELINE_MAX_TWEETS = int(os.environ.get("TIMELINE_MAX_TWEETS", "30"))

# Credentials
X_USERNAME = os.environ.get("X_USERNAME", "")
X_PASSWORD = os.environ.get("X_PASSWORD", "")
X_EMAIL = os.environ.get("X_EMAIL", "")
