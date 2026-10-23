from datetime import UTC, datetime, timedelta

from anthropic import Anthropic
from sqlalchemy.orm import Session

from ai_news_radar.config import ANTHROPIC_API_KEY, CLASSIFIER_MODEL
from ai_news_radar.models import Development, RawItem

# Karar 3 benzeri: haftalik ozet de LLM'e verilen gercek, siniflandirilmis
# gelismelere dayanir - uydurma icerik eklenmez, sadece sentezler.
SYSTEM_PROMPT = """Sen bir AI/teknoloji haber editorusun. Sana son bir haftanin
en oncelikli, zaten dogrulanmis AI gelismelerinin basliklari, oncelik skorlari
ve sektorleri verilecek. Gorevin bunlardan 3-5 cumlelik, akici Turkce bir
"bu hafta AI'da neler oldu" ozeti yazmak - somut, iddiasiz, gazete girisi gibi.
SADECE sana verilen gelismelere dayan, baska hicbir sey uydurma. SADECE ozet
paragrafini dondur, baslik veya baska metin ekleme."""


def generate_weekly_digest(session: Session, limit: int = 15) -> tuple[str, int]:
    since = datetime.now(UTC) - timedelta(days=7)
    top = (
        session.query(Development)
        .join(RawItem, Development.raw_item_id == RawItem.id)
        .filter(Development.verified.is_(True))
        .filter(RawItem.fetched_at >= since)
        .order_by(Development.priority_score.desc())
        .limit(limit)
        .all()
    )
    if not top:
        return "Son bir haftada doğrulanmış yeni gelişme bulunamadı.", 0

    lines = [
        f"- {d.title_tr or d.raw_item.title} "
        f"(öncelik {d.priority_score}, sektörler: {', '.join(d.sector_tags or []) or 'belirtilmemis'})"
        for d in top
    ]

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLASSIFIER_MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "\n".join(lines)}],
    )
    return message.content[0].text.strip(), len(top)
