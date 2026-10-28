"""Table-based, self-contained newsletter; no tracking or remote images."""
from datetime import UTC
from html import escape, unescape
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from ai_news_radar.ingestion.base import strip_html

TAGS = {"nlp": "Dil modelleri", "general_software": "Yazılım", "robotics": "Robotik",
        "enterprise": "Kurumsal AI", "healthcare": "Sağlık", "education": "Eğitim",
        "autonomous_systems": "Otonom sistemler", "cybersecurity": "Siber güvenlik",
        "design": "Tasarım", "manufacturing": "Üretim", "defense": "Savunma"}


def safe_url(value):
    try:
        parts = urlsplit(value or "")
        if parts.scheme in ("https", "http") and parts.hostname and not parts.username and not any(ord(c) < 32 for c in value):
            return value
    except ValueError:
        pass
    return ""


def source_name(story):
    name = story.raw_item.source.name
    if name.startswith("yt-"):
        return "YouTube · " + name[3:].replace("-", " ").title()
    return {"arxiv": "arXiv", "openai-news": "OpenAI", "huggingface-blog": "Hugging Face",
            "nvidia-blog": "NVIDIA", "ollama-blog": "Ollama", "lm-studio-blog": "LM Studio"}.get(name, name.replace("-", " ").title())


def stamp(story, timezone):
    raw = story.raw_item
    date = raw.published_at or raw.fetched_at
    if not date:
        return "Yayın tarihi belirtilmemiş"
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)
    label = date.astimezone(ZoneInfo(timezone)).strftime("%d.%m · %H:%M")
    return label + (" · Radara alınma" if not raw.published_at else "")


def summary(story):
    return unescape(strip_html(story.summary_tr or story.raw_item.summary or "")).strip()[:1200]


def related_stories(story):
    return getattr(story, "related_sources", ())


def related_html(story):
    links = []
    for related in related_stories(story):
        url = safe_url(related.raw_item.url)
        if url:
            links.append(f'<a href="{escape(url, quote=True)}" style="color:#087e7c;text-decoration:underline;">{escape(source_name(related))}</a>')
    if not links:
        return ""
    return '<p style="margin:14px 0 0;font-size:12px;line-height:1.8;color:#697279;"><strong>Diğer kaynaklar:</strong> ' + ' · '.join(links) + '</p>'


def story_html(story, index, timezone):
    title = escape(story.title_tr or story.raw_item.title)
    text = escape(summary(story))
    rationale = escape(unescape(strip_html(story.classification_rationale or "")).strip()[:650])
    tags = " · ".join(TAGS.get(tag, tag.replace("_", " ")) for tag in (story.sector_tags or [])[:3])
    url = safe_url(story.raw_item.url)
    link = f'<a href="{escape(url, quote=True)}" style="color:#087e7c;text-decoration:underline;font-size:14px;font-weight:bold;">Orijinal kaynağı oku →</a>' if url else ''
    heading = f'<a href="{escape(url, quote=True)}" style="color:#17191c;text-decoration:none;">{title}</a>' if url else title
    importance = f'<p style="margin:14px 0 0;padding-left:12px;border-left:2px solid #18a5a1;font-size:14px;line-height:1.65;color:#4d555b;"><strong style="color:#17191c;">Neden önemli?</strong><br>{rationale}</p>' if rationale else ''
    marker = 'ÖNE ÇIKAN GELİŞME' if index == 1 else 'GÜNÜN AKIŞI'
    heading_size, heading_weight = (27, 700) if index == 1 else (18, 600)
    parts = [
        f'<p style="margin:0 0 12px;color:#087e7c;font-size:11px;font-weight:bold;letter-spacing:1px;">{index:02d} / {marker}</p>',
        f'<h2 style="margin:0 0 10px;font-size:{heading_size}px;line-height:1.3;letter-spacing:-.3px;font-weight:{heading_weight};">{heading}</h2>',
        f'<p style="margin:0 0 14px;color:#697279;font-size:12px;line-height:1.6;">{escape(source_name(story))} &nbsp;·&nbsp; {escape(stamp(story, timezone))}</p>',
        f'<p style="margin:0;color:#30383e;font-size:15px;line-height:1.8;">{text or "Yayıncı bu haber için kısa bir özet paylaşmadı. Ayrıntılar için orijinal kaynağı açabilirsin."}</p>',
        importance,
        f'<p style="margin:16px 0 10px;color:#697279;font-size:11px;line-height:1.6;">{escape(tags)}</p>{link}{related_html(story)}',
    ]
    body = '\n      '.join(part for part in parts if part)
    return f'<tr><td class="content" style="padding:26px 32px;border-top:1px solid #e2e7e7;">\n      {body}\n    </td></tr>'


def render_html(stories, date_label, *, timezone="Europe/Istanbul", public_url=""):
    count = len(stories)
    sources = len({coverage.raw_item.source.name for story in stories for coverage in (story, *related_stories(story))})
    body = ''.join(story_html(story, index, timezone) for index, story in enumerate(stories, 1))
    if not stories:
        body = '<tr><td class="content" style="padding:32px;color:#4d555b;line-height:1.8;">Son 24 saatte bültene uygun yeni gelişme bulunamadı. Yeni haber bulunmadığında eski içerikler bugünün haberi olarak sunulmaz.</td></tr>'
    url = safe_url(public_url)
    cta = f'<p style="margin:0 0 22px;"><a href="{escape(url, quote=True)}" style="display:inline-block;padding:13px 20px;background:#17191c;color:#ffffff;text-decoration:none;font-size:14px;border-radius:6px;">Radar’da tüm haberleri aç →</a></p>' if url else ''
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Radar · Günlük AI Özeti · {escape(date_label)}</title>
<style>@media only screen and (max-width:620px){{.outer{{padding:12px 8px!important;}}.content{{padding-left:20px!important;padding-right:20px!important;}}.brand{{width:235px!important;max-width:100%!important;height:auto!important;}}}}</style></head>
<body style="margin:0;padding:0;background:#edf1f1;font-family:Arial,Helvetica,sans-serif;color:#17191c;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(date_label)} · {count} seçili AI haberi. Dil modelleri, araştırmalar ve uygulamalar; kaynaklarıyla günlük Radar özeti.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td class="outer" align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:620px;background:#ffffff;border:1px solid #dce3e3;">
<tr><td class="content" style="background:#0f2b26;padding:8px 28px;border-bottom:4px solid #18a5a1;">
<img class="brand" src="cid:radar-logo" width="260" height="145" alt="Radar — AI News Detect &amp; Blog" style="display:block;width:260px;height:145px;max-width:100%;border:0;"></td></tr>
<tr><td class="content" style="padding:30px 32px 26px;">
<p style="margin:0 0 12px;font-size:11px;letter-spacing:1.2px;color:#087e7c;font-weight:bold;">GÜNLÜK BÜLTEN &nbsp;/&nbsp; {escape(date_label)}</p>
<h1 style="margin:0 0 14px;font-size:32px;line-height:1.2;letter-spacing:-.8px;">Günün AI gündemi.</h1>
<p style="margin:0 0 24px;color:#4d555b;font-size:15px;line-height:1.8;">Araştırmalar, dil modelleri ve pratik uygulamalar. Son 24 saatin seçili gelişmeleri; ne olduğu, neden önemli olduğu ve orijinal kaynaklarıyla.</p>
<p style="margin:0 0 24px;color:#697279;font-size:12px;line-height:1.6;">{count:02d} seçili haber &nbsp;·&nbsp; {sources:02d} kaynak &nbsp;·&nbsp; son 24 saat</p></td></tr>{body}
<tr><td class="content" style="padding:26px 32px;background:#f6f8f8;border-top:1px solid #e2e7e7;">{cta}
<p style="margin:0 0 10px;font-size:13px;font-weight:bold;">Kaynağı incele. Bağlamı anla.</p>
<p style="margin:0;color:#697279;font-size:11px;line-height:1.8;">Bu bülten Radar’ın kaynak politikasına göre seçilir; bağımsız çapraz teyit anlamına gelmez. Teyit bekleyen sosyal paylaşımlar dahil edilmez. Yayın tarihi olmayan içeriklerde Radara alınma zamanı gösterilir.<br>Saat dilimi: {escape(timezone)} · Radar günlük AI özeti</p>
</td></tr></table></td></tr></table></body></html>'''


def render_text(stories, date_label, *, timezone="Europe/Istanbul"):
    lines = [f"RADAR · Günlük AI Özeti · {date_label}", f"Son 24 saat · {len(stories)} seçili haber", ""]
    for index, story in enumerate(stories, 1):
        lines.extend([f"{index:02d}. {unescape(strip_html(story.title_tr or story.raw_item.title))}",
                      f"{source_name(story)} · {stamp(story, timezone)}", summary(story)])
        if story.classification_rationale:
            lines.append("Neden önemli? " + unescape(strip_html(story.classification_rationale)))
        if safe_url(story.raw_item.url):
            lines.append(story.raw_item.url)
        for related in related_stories(story):
            if safe_url(related.raw_item.url):
                lines.append(f"Diğer kaynaklar · {source_name(related)}: {related.raw_item.url}")
        lines.append("")
    if not stories:
        lines.append("Son 24 saatte bültene uygun yeni gelişme bulunamadı.")
    lines.append("Radar kaynak politikasına göre seçilmiştir; bağımsız çapraz teyit anlamına gelmez.")
    return '\n'.join(lines)
