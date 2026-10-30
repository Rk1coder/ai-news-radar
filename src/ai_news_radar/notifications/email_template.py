"""Table-based, self-contained newsletter; no tracking or remote images."""
from datetime import UTC
from html import escape, unescape
from zoneinfo import ZoneInfo

from ai_news_radar.ingestion.base import strip_html
from ai_news_radar.notifications.email_content import reading_minutes, safe_url, sections, try_today

TAGS = {"nlp": "Dil modelleri", "general_software": "Yazılım", "robotics": "Robotik",
        "enterprise": "Kurumsal AI", "healthcare": "Sağlık", "education": "Eğitim",
        "autonomous_systems": "Otonom sistemler", "cybersecurity": "Siber güvenlik",
        "design": "Tasarım", "manufacturing": "Üretim", "defense": "Savunma",
        "finance": "Finans", "entertainment": "Eğlence", "productivity": "Üretkenlik",
        "advertising": "Reklam", "marketing": "Pazarlama", "government": "Kamu",
        "e-commerce": "E-ticaret"}


def source_name(story):
    name = story.raw_item.source.name
    if name.startswith("yt-"):
        return "YouTube · " + name[3:].replace("-", " ").title()
    return {"arxiv": "arXiv", "openai-news": "OpenAI", "huggingface-blog": "Hugging Face",
            "nvidia-blog": "NVIDIA", "ollama-blog": "Ollama", "lm-studio-blog": "LM Studio",
            "n8n-blog": "n8n", "deepmind-blog": "Google DeepMind", "aws-ml-blog": "AWS",
            "arstechnica-ai": "Ars Technica", "theverge-ai": "The Verge",
            "techcrunch-ai": "TechCrunch", "the-decoder": "The Decoder",
            "masqot-blog": "Masqot"}.get(name, name.replace("-", " ").title())


def stamp(story, timezone):
    raw = story.raw_item
    date = raw.published_at or raw.fetched_at
    if not date:
        return "Yayın tarihi belirtilmemiştir"
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)
    label = date.astimezone(ZoneInfo(timezone)).strftime("%d.%m · %H:%M")
    return label + (" · Radar’a eklenme zamanı" if not raw.published_at else "")


def summary(story):
    return unescape(strip_html(story.summary_tr or story.raw_item.summary or "")).strip()[:1200]


def related_stories(story):
    return getattr(story, "related_sources", ())


def related_html(story):
    links = []
    for related in related_stories(story):
        url = safe_url(related.raw_item.url)
        if url:
            links.append(f'<a href="{escape(url, quote=True)}" style="color:#0a7f7c;text-decoration:underline;">{escape(source_name(related))}</a>')
    if not links:
        return ""
    return '<p style="margin:12px 0 0;font-size:12px;line-height:1.7;color:#646873;"><strong>Diğer kaynaklar:</strong> ' + ' · '.join(links) + '</p>'


def story_html(story, index, timezone, *, recommended=False, featured=False, image=None):
    title = escape(story.title_tr or story.raw_item.title)
    text = escape(summary(story)) or "Bu haber için kısa bir özet paylaşılmamıştır. Ayrıntılara orijinal kaynaktan ulaşılabilir."
    rationale = escape(unescape(strip_html(story.classification_rationale or "")).strip()[:650])
    tags = " · ".join(TAGS.get(tag, tag.replace("_", " ")) for tag in (story.sector_tags or [])[:3])
    url = safe_url(story.raw_item.url)
    link_label = 'Proje veya yayın duyurusu →' if recommended else 'Orijinal kaynak →'
    link = f'<a href="{escape(url, quote=True)}" style="color:#0a7f7c;text-decoration:underline;font-size:13px;font-weight:bold;">{link_label}</a>' if url else ''
    heading = f'<a href="{escape(url, quote=True)}" style="color:#17191c;text-decoration:none;">{title}</a>' if url else title
    marker = 'Bugün denenebilecekler' if recommended else f'{index:02d} / GELİŞME'
    label = f'<p style="margin:0 0 10px;font:11px/1.5 Courier New,Courier,monospace;letter-spacing:1px;color:#0a7f7c;">{marker}</p>'
    headline = f'<h3 style="margin:0 0 10px;font-size:{26 if featured else 21}px;line-height:1.25;letter-spacing:-.5px;font-weight:600;color:#17191c;">{heading}</h3>'
    metadata = f'<p style="margin:0 0 12px;color:#646873;font-size:12px;line-height:1.6;">{escape(source_name(story))}<br>{escape(stamp(story, timezone))}</p>'
    importance = f'<p style="margin:12px 0 0;font-size:13px;line-height:1.65;color:#646873;"><strong style="color:#17191c;">Neden önemli?</strong> {rationale}</p>' if rationale else ''
    tag_line = f'<p style="margin:12px 0 8px;color:#646873;font-size:11px;line-height:1.6;">{escape(tags)}</p>' if tags else ''
    detail = f'<p style="margin:0;color:#17191c;font-size:15px;line-height:1.65;">{text}</p>{importance}{tag_line}<p style="margin:10px 0 0;">{link}</p>{related_html(story)}'
    if image:
        is_logo = image.kind == 'source_logo'
        image_label = f'Kaynak logosu: {source_name(story)}' if is_logo else f'{source_name(story)} haberinin kapak görseli'
        width = 72 if is_logo else 210
        photo = f'<img class="story-image" src="cid:{escape(image.cid, quote=True)}" width="{width}" alt="{escape(image_label, quote=True)}" style="display:block;width:{"72px" if is_logo else "100%"};max-width:100%;height:auto;border:0;border-radius:8px;">'
        if url:
            photo = f'<a href="{escape(url, quote=True)}">{photo}</a>'
        caption_label = image_label if is_logo else f'Kaynak: {source_name(story)}'
        caption = f'<p style="margin:8px 0 0;font-size:10px;line-height:1.5;color:#646873;">{escape(caption_label)}</p>'
        article = f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="table-layout:fixed;">
<tr><td class="story-heading" width="38%" valign="top" style="padding:0 24px 0 0;">{photo}{caption}</td>
<td class="story-detail" width="62%" valign="top" style="padding:0;">{label}{headline}{metadata}{detail}</td></tr></table>'''
    elif featured:
        article = f'''<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="table-layout:fixed;">
<tr><td class="story-heading" width="38%" valign="top" style="padding:0 24px 0 0;">{label}{headline}{metadata}</td>
<td class="story-detail" width="62%" valign="top" style="padding:0;">{detail}</td></tr></table>'''
    else:
        article = f'{label}{headline}{metadata}{detail}'
    if recommended:
        article = f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding:20px;background:#fbe1d1;border-left:3px solid #0a7f7c;">{article}</td></tr></table>'
    return f'<tr><td class="content" style="padding:0 24px 26px;">{article}</td></tr>'


def render_html(stories, date_label, *, timezone="Europe/Istanbul", public_url="", images=None):
    count = len(stories)
    sources = len({coverage.raw_item.source.name for story in stories for coverage in (story, *related_stories(story))})
    recommended = try_today(stories)
    body_parts, index = [], 0
    for name, items in sections(stories):
        body_parts.append(f'''<tr><td class="content" style="padding:12px 24px 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding:18px 0 0;border-top:1px solid #e4e4e6;">
<h2 style="margin:0;color:#17191c;font:500 17px/1.5 Courier New,Courier,monospace;letter-spacing:2px;">{escape(name)}</h2>
<p style="margin:5px 0 0;color:#646873;font:11px/1.5 Courier New,Courier,monospace;">{len(items):02d} GELİŞME</p></td></tr></table></td></tr>''')
        for position, story in enumerate(items):
            index += 1
            body_parts.append(story_html(story, index, timezone, recommended=story is recommended,
                                         featured=position == 0, image=(images or {}).get(story.raw_item.url)))
    body = ''.join(body_parts)
    reading = f' &nbsp;·&nbsp; Yaklaşık {reading_minutes(_text_body(stories, timezone))} dakika' if stories else ''
    if not stories:
        body = '<tr><td class="content" style="padding:24px;color:#646873;font-size:16px;line-height:1.8;">Son 24 saatte bültene uygun yeni gelişme bulunamadı. Yeni haber bulunmadığında eski içerikler bugünün haberi olarak sunulmaz.</td></tr>'
    url = safe_url(public_url)
    cta = f'<p style="margin:0 0 22px;"><a href="{escape(url, quote=True)}" style="color:#0a7f7c;text-decoration:underline;font-size:14px;font-weight:bold;">Radar’daki tüm haberler →</a></p>' if url else ''
    return f'''<!doctype html><html lang="tr" xmlns:o="urn:schemas-microsoft-com:office:office"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Radar · Günlük AI Özeti · {escape(date_label)}</title>
<!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml><![endif]-->
<style>body,table,td,p,a{{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}}table{{border-collapse:collapse;mso-table-lspace:0;mso-table-rspace:0;}}img{{-ms-interpolation-mode:bicubic;}}a{{overflow-wrap:anywhere;}}h1,h2,h3,p{{overflow-wrap:break-word;}}
@media only screen and (max-width:600px){{.outer{{padding:0!important;}}.content{{padding-left:20px!important;padding-right:20px!important;}}.masthead{{font-size:72px!important;letter-spacing:-5px!important;}}.edition-title{{font-size:34px!important;}}.story-heading,.story-detail{{display:block!important;width:100%!important;box-sizing:border-box!important;}}.story-heading{{padding:0 0 10px!important;}}.brand{{width:112px!important;height:auto!important;}}.edition-date{{font-size:11px!important;}}}}</style></head>
<body style="margin:0;padding:0;background:#fafafb;font-family:Arial,Helvetica,sans-serif;color:#17191c;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;mso-hide:all;">{escape(date_label)} · {count} seçili AI haberi. Dil modelleri, araştırmalar ve uygulamalar; kaynaklarıyla günlük Radar özeti.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#fafafb"><tr><td class="outer" align="center" style="padding:20px 12px 40px;">
<!--[if mso]><table role="presentation" width="600" align="center"><tr><td><![endif]-->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;table-layout:fixed;background:#ffffff;">
<tr><td class="content" style="padding:22px 24px 18px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td class="edition-date" valign="middle" style="font:12px/1.8 Courier New,Courier,monospace;color:#0a7f7c;letter-spacing:1px;">{escape(date_label)}<br>GÜNLÜK AI BÜLTENİ</td>
<td align="right" valign="middle"><img class="brand" src="cid:radar-logo" width="132" height="74" alt="Radar — AI News Detect &amp; Blog" style="display:block;width:132px;height:74px;border:0;"></td></tr></table></td></tr>
<tr><td class="content" style="padding:0 24px 28px;">
<p class="masthead" style="margin:0;color:#0a7f7c;font-size:100px;line-height:1;letter-spacing:-7px;font-weight:900;">RADAR</p>
<p style="margin:14px 0 0;font:11px/1.7 Courier New,Courier,monospace;color:#646873;letter-spacing:1px;">YAPAY ZEKÂ · ARAŞTIRMA · TEKNOLOJİ</p></td></tr>
<tr><td class="content" style="padding:26px 24px;background:#fbe1d1;">
<h1 class="edition-title" style="margin:0 0 18px;font-size:44px;line-height:1.08;letter-spacing:-1.6px;font-weight:500;color:#5d2a1a;">Günün yapay zekâ<br>gündemi.</h1>
<p style="margin:0 0 18px;color:#646873;font-size:15px;line-height:1.65;">Dil modelleri, araştırmalar ve araçlara ilişkin gelişmeler kaynaklarıyla birlikte derlenmiştir.</p>
<p style="margin:0;color:#646873;font:11px/1.9 Courier New,Courier,monospace;">{count:02d} seçili haber &nbsp;·&nbsp; {sources:02d} kaynak &nbsp;·&nbsp; son 24 saat{reading}</p></td></tr>{body}
<tr><td class="content" style="padding:12px 24px 0;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td style="padding:28px 0;border-top:1px solid #e4e4e6;">
<p style="margin:0 0 16px;font-size:36px;line-height:1.12;letter-spacing:-1px;color:#17191c;">Gündem derlendi.</p>
<p style="margin:0 0 18px;font-size:14px;line-height:1.7;">Haberler kaynaklarıyla birlikte sunulmuştur.</p>{cta}
<p style="margin:0;color:#646873;font-size:11px;line-height:1.8;">İçerikler Radar’ın kaynak politikasına göre seçilmiştir; bağımsız çapraz teyit yapıldığı ileri sürülmemektedir. Teyit bekleyen sosyal paylaşımlar bültene dâhil edilmemiştir. Yayın tarihi belirtilmeyen içeriklerde Radar’a eklenme zamanı gösterilmiştir.</p>
<p style="margin:22px 0 0;color:#646873;font:10px/1.8 Courier New,Courier,monospace;letter-spacing:.5px;">RADAR · GÜNLÜK YAPAY ZEKÂ ÖZETİ<br>Saat dilimi: {escape(timezone)}</p>
</td></tr></table></td></tr></table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table></body></html>'''


def _text_body(stories, timezone):
    lines, index = [], 0
    recommended = try_today(stories)
    for name, items in sections(stories):
        lines.extend([name, ""])
        for story in items:
            index += 1
            if story is recommended:
                lines.append("Bugün denenebilecekler")
            lines.extend([f"{index:02d}. {unescape(strip_html(story.title_tr or story.raw_item.title))}",
                          f"{source_name(story)} · {stamp(story, timezone)}", summary(story)])
            if story.classification_rationale:
                lines.append("Neden önemli? " + unescape(strip_html(story.classification_rationale)).strip()[:650])
            if safe_url(story.raw_item.url):
                lines.append(story.raw_item.url)
            for related in related_stories(story):
                if safe_url(related.raw_item.url):
                    lines.append(f"Diğer kaynaklar · {source_name(related)}: {related.raw_item.url}")
            lines.append("")
    if not stories:
        lines.append("Son 24 saatte bültene uygun yeni gelişme bulunamadı.")
    lines.append("İçerikler Radar’ın kaynak politikasına göre seçilmiştir; bağımsız çapraz teyit yapıldığı ileri sürülmemektedir.")
    return '\n'.join(lines)


def render_text(stories, date_label, *, timezone="Europe/Istanbul"):
    body = _text_body(stories, timezone)
    reading = f" · Yaklaşık {reading_minutes(body)} dakika" if stories else ""
    return f"RADAR · Günlük AI Özeti · {date_label}\nSon 24 saat · {len(stories)} seçili haber{reading}\n\n{body}"
