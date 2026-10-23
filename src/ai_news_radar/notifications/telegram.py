import requests

from ai_news_radar.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from ai_news_radar.models import Development

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def _format_message(development: Development) -> str:
    raw = development.raw_item
    sectors = ", ".join(development.sector_tags) if development.sector_tags else "-"
    return (
        f"#{development.priority_score} - {raw.title}\n"
        f"etki={development.technical_impact_score} "
        f"hype={development.hype_score} "
        f"uygulanabilirlik={development.applicability_score}\n"
        f"sektorler: {sectors}\n"
        f"{raw.url}"
    )


def notify_telegram(development: Development) -> None:
    """Karar: cikti formati -> Telegram bildirim kanali.

    Dogrulanmis+siniflandirilmis her yeni gelisme icin gruba mesaj yollar.
    Telegram API hatasi pipeline'i durdurmamali - sadece uyari basilir.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN),
            json={"chat_id": TELEGRAM_CHAT_ID, "text": _format_message(development)},
            timeout=10,
        )
    except requests.RequestException as exc:
        print(f"[telegram] bildirim gonderilemedi: {exc}")
