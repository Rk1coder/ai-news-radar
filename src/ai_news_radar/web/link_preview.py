import re

import requests

USER_AGENT = "Mozilla/5.0 (compatible; ai-news-radar/0.1)"
_META_TAG_RE = re.compile(r"<meta\s+[^>]*>", re.IGNORECASE)
_ATTR_RE = re.compile(r"""(\w[\w:-]*)\s*=\s*"([^"]*)"|(\w[\w:-]*)\s*=\s*'([^']*)'""")


def _parse_attrs(tag: str) -> dict[str, str]:
    attrs = {}
    for match in _ATTR_RE.finditer(tag):
        if match.group(1):
            attrs[match.group(1).lower()] = match.group(2)
        else:
            attrs[match.group(3).lower()] = match.group(4)
    return attrs


def extract_og_meta(html: str) -> dict[str, str]:
    """<meta property/name=... content=...> etiketlerinden og: alanlarini cikarir."""
    result: dict[str, str] = {}
    for tag in _META_TAG_RE.findall(html):
        attrs = _parse_attrs(tag)
        key = attrs.get("property") or attrs.get("name")
        content = attrs.get("content")
        if not key or not content:
            continue
        if key in ("og:image", "twitter:image") and "image" not in result:
            result["image"] = content
        elif key in ("og:description", "description") and "description" not in result:
            result["description"] = content
        elif key == "og:title" and "title" not in result:
            result["title"] = content
    return result


def fetch_link_preview(url: str) -> dict[str, str]:
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return {}
    return extract_og_meta(response.text)
