import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    return _TAG_RE.sub(" ", text)


@dataclass
class FetchedItem:
    """Bir connector'in dondurdugu, henuz DB'ye yazilmamis ham icerik."""

    external_id: str
    title: str
    url: str
    summary: str
    published_at: datetime | None


class Connector(Protocol):
    """Karar 1-A: her kaynak turu kendi connector'inda, bagimsiz, test edilebilir."""

    source_name: str
    source_type: str  # academic | company | defense | social

    def fetch(self) -> list[FetchedItem]:
        ...
