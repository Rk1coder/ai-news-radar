"""Local presentation rules for the daily digest; never invent news or links."""
import math
import re
import unicodedata
from urllib.parse import urlsplit

from ai_news_radar.ingestion.base import strip_html

TOPICS = ("LLM & Yerel Modeller", "Araştırma", "Araçlar & Uygulamalar", "Diğer gelişmeler")


def normalize(text):
    text = strip_html(text or "").casefold().replace("ı", "i")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def safe_url(value):
    try:
        parts = urlsplit(value or "")
        if parts.scheme in ("https", "http") and parts.hostname and not parts.username and not any(ord(c) < 32 for c in value):
            return value
    except ValueError:
        pass
    return ""


def _text(story):
    return normalize(" ".join((story.title_tr or "", story.raw_item.title or "",
                               story.summary_tr or "", story.raw_item.summary or "")))


def _artifact(story):
    parts = urlsplit(safe_url(story.raw_item.url))
    path = [p for p in parts.path.split("/") if p]
    if parts.hostname == "github.com" and len(path) == 2 and path[0] not in {"topics", "orgs", "settings", "collections", "marketplace", "features"}:
        return "project"
    if parts.hostname == "huggingface.co":
        if len(path) == 2 and path[0] not in {"blog", "docs", "papers", "datasets", "spaces", "collections", "organizations", "settings", "learn"}:
            return "model"
        if len(path) == 3 and path[0] == "spaces":
            return "project"
    return ""


def topic(story):
    text = _text(story)
    if story.raw_item.source.source_type == "academic" or story.raw_item.source.name == "arxiv":
        return TOPICS[1]
    headline = normalize((story.title_tr or "") + " " + (story.raw_item.title or ""))
    if re.search(r"yatirim|fonlama|funding|raises |investment|acquisition|satin al|gartner|magic quadrant", headline):
        return TOPICS[3]
    if (_artifact(story) == "model" or "nlp" in (story.sector_tags or [])
            or re.search(r"\b(llms?|vllm|ollama|llama|deepseek|qwen|gemma|gpt|gemini|mistral)\b|dil modeli|dil modeller|language models?|yerel model|local model|acik agirlik|open.weight", text)):
        return TOPICS[0]
    if re.search(r"\b(research|paper|study|arxiv|benchmark)\b|arastirma|bilimsel|calismasi", text):
        return TOPICS[1]
    if (_artifact(story) == "project" or "general_software" in (story.sector_tags or [])
            or re.search(r"\b(tool|tools|app|apps|editor|browser|workflow|n8n|software)\b|arac|uygulama|editor|tarayici|otomasyon|yazilim", text)):
        return TOPICS[2]
    return TOPICS[3]


def sections(stories):
    grouped = {name: [] for name in TOPICS}
    for story in stories:
        grouped[topic(story)].append(story)
    return [(name, items) for name, items in grouped.items() if items]


def try_today(stories):
    """Select one accessible artifact or official release, using existing links only."""
    for story in stories:
        if not safe_url(story.raw_item.url):
            continue
        text = _text(story)
        if re.search(r"coming soon|waitlist|wait.list|not yet available|research preview|yakinda|bekleme list|henuz.{0,40}(?:acilmadi|sunulmadi|kullanilam)|kullanima acilacak|guvenlik acigi|vulnerab|exploit|discontinued|kaldirildi", text):
            continue
        if _artifact(story):
            return story
        host = urlsplit(story.raw_item.url).hostname
        official = {"n8n-blog": "blog.n8n.io", "ollama-blog": "ollama.com",
                    "lm-studio-blog": "lmstudio.ai"}
        if (official.get(story.raw_item.source.name) == host
                and re.search(r"\b(released?|available|introducing|launched?)\b|yayi[mn]landi|kullanilabilir|kullanima sunuldu|tanitil", text)):
            return story
    return None


def reading_minutes(text):
    # Links are navigation rather than reading; count the actual readable copy.
    text = re.sub(r"https?://\S+", "", text)
    words = re.findall(r"\b\w+(?:['’\-]\w+)*\b", strip_html(text))
    return max(1, math.ceil(len(words) / 200))
