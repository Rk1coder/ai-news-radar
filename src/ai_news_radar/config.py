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

# Daily digest email (e.g. via Proton Mail Bridge's local SMTP).
EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "false").lower() == "true"
EMAIL_SMTP_HOST = os.environ.get("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = int(os.environ.get("EMAIL_SMTP_PORT", "1025"))
EMAIL_SMTP_SECURITY = os.environ.get("EMAIL_SMTP_SECURITY", "starttls").lower()
if EMAIL_SMTP_SECURITY not in ("starttls", "ssl", "local"):
    raise ValueError("EMAIL_SMTP_SECURITY must be starttls, ssl or local")
EMAIL_SMTP_USER = os.environ.get("EMAIL_SMTP_USER", "")
EMAIL_SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "") or EMAIL_SMTP_USER
EMAIL_PUBLIC_URL = os.environ.get("EMAIL_PUBLIC_URL", "").rstrip("/")
EMAIL_RECIPIENTS = tuple(a.strip() for a in os.environ.get("EMAIL_RECIPIENTS", "").split(",") if a.strip())
# Local hour (SCAN_TIMEZONE) at/after which the daily digest goes out; sent once per day.
EMAIL_SEND_HOUR = int(os.environ.get("EMAIL_SEND_HOUR", "16"))
if not 0 <= EMAIL_SEND_HOUR <= 23:
    raise ValueError("EMAIL_SEND_HOUR must be between 0 and 23")

AUTO_SCAN_ENABLED = os.environ.get("AUTO_SCAN_ENABLED", "true").lower() == "true"
SCAN_TIMEZONE = os.environ.get("SCAN_TIMEZONE", "Europe/Istanbul")
SCAN_HOURS = tuple(sorted({int(h.strip()) for h in os.environ.get("SCAN_HOURS", "6,10,14,18,22").split(",")}))
if not SCAN_HOURS or any(h < 0 or h > 23 for h in SCAN_HOURS):
    raise ValueError("SCAN_HOURS must contain hours between 0 and 23")

# Set to 0 to use the daily program; SCAN_HOURS supplies its initial times.
SCAN_INTERVAL_MINUTES = int(os.environ.get("SCAN_INTERVAL_MINUTES", "15"))
if SCAN_INTERVAL_MINUTES not in (0, 5, 10, 15, 20, 30, 60):
    raise ValueError("SCAN_INTERVAL_MINUTES must be 0, 5, 10, 15, 20, 30 or 60")
