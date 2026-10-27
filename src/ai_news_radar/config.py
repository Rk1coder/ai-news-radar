import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://radar:radar@localhost:5432/ai_news_radar"
)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLASSIFIER_MODEL = os.environ.get("CLASSIFIER_MODEL", "claude-haiku-4-5")

TELEGRAM_ENABLED = os.environ.get("TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

AUTO_SCAN_ENABLED = os.environ.get("AUTO_SCAN_ENABLED", "true").lower() == "true"
SCAN_TIMEZONE = os.environ.get("SCAN_TIMEZONE", "Europe/Istanbul")
SCAN_HOURS = tuple(sorted({int(h.strip()) for h in os.environ.get("SCAN_HOURS", "6,10,14,18,22").split(",")}))
if not SCAN_HOURS or any(h < 0 or h > 23 for h in SCAN_HOURS):
    raise ValueError("SCAN_HOURS must contain hours between 0 and 23")

# Set to 0 to use the legacy daily SCAN_HOURS schedule.
SCAN_INTERVAL_MINUTES = int(os.environ.get("SCAN_INTERVAL_MINUTES", "15"))
if SCAN_INTERVAL_MINUTES not in (0, 5, 10, 15, 20, 30, 60):
    raise ValueError("SCAN_INTERVAL_MINUTES must be 0, 5, 10, 15, 20, 30 or 60")
