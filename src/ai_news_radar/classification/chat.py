import re

import requests
from anthropic import Anthropic

from ai_news_radar.config import ANTHROPIC_API_KEY, CLASSIFIER_MODEL
from ai_news_radar.ingestion.base import strip_html
from ai_news_radar.models import Development

USER_AGENT = "Mozilla/5.0 (compatible; ai-news-radar/0.1)"
_WHITESPACE_RE = re.compile(r"\s+")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)

SYSTEM_PROMPT = """Sen bir AI/teknoloji gelismesi hakkinda soru-cevap yapan bir asistansin.
Sana asagida bir gelismenin baslik, ozet, siniflandirma gerekcesi, skorlari ve (varsa)
orijinal makalenin metni verilecek. Kullanicinin sorularini SADECE bu bilgiye dayanarak,
Turkce ve acik bir dille yanitla. Elindeki bilgi soruyu yanitlamaya yetmiyorsa bunu acikca
soyle, uydurma bilgi verme. Teknik terimleri gerektiginde kisaca acikla."""


def _fetch_article_text(url: str, max_chars: int = 6000) -> str:
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return ""
    html = _SCRIPT_STYLE_RE.sub(" ", response.text)
    text = _WHITESPACE_RE.sub(" ", strip_html(html)).strip()
    return text[:max_chars]


def _build_context(development: Development) -> str:
    raw = development.raw_item
    lines = [
        f"BASLIK: {development.title_tr or raw.title}",
        f"KAYNAK: {raw.source.name} ({raw.source.source_type})",
        f"OZET: {development.summary_tr or raw.summary or '(yok)'}",
    ]
    if development.verified:
        lines.append(f"SINIFLANDIRMA GEREKCESI: {development.classification_rationale}")
        lines.append(
            f"SKORLAR: teknik etki {development.technical_impact_score}, "
            f"hype {development.hype_score}, uygulanabilirlik {development.applicability_score}, "
            f"oncelik {development.priority_score}"
        )
        lines.append(f"SEKTORLER: {', '.join(development.sector_tags or [])}")
    else:
        lines.append(f"DURUM: Henuz dogrulanmadi - {development.verification_notes}")

    article_text = _fetch_article_text(raw.url)
    if article_text:
        lines.append(f"ORIJINAL MAKALE METNI: {article_text}")

    return "\n".join(lines)


def answer_question(
    development: Development, question: str, history: list[dict[str, str]] | None = None
) -> str:
    context = _build_context(development)
    messages = [{"role": "user", "content": f"BAGLAM:\n{context}"}]
    messages.append({"role": "assistant", "content": "Anladim, sorularini bu baglama dayanarak yanitlayacagim."})
    for turn in history or []:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=CLASSIFIER_MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text.strip()
