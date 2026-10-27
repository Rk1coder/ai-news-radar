"""Mevcut Development kayitlarinin title_tr/summary_tr alanlarini yeniden cevirir.

Skorlari/etiketleri degistirmez - sadece ceviriyi yeniler (duzeltilmis Turkce
yazim kurallarini uygulamak icin).

Calistirma: python -m ai_news_radar.retranslate [--from-id N] [--limit N]
"""

import sys
import time

from ai_news_radar.classification.llm_classifier import translate
from ai_news_radar.db import get_session
from ai_news_radar.models import Development


def _arg(flag: str) -> int | None:
    if flag in sys.argv:
        return int(sys.argv[sys.argv.index(flag) + 1])
    return None


def main() -> None:
    from_id = _arg("--from-id")
    limit = _arg("--limit")
    session = get_session()
    try:
        query = session.query(Development).order_by(Development.id)
        if from_id is not None:
            query = query.filter(Development.id >= from_id)
        developments = query.limit(limit).all() if limit else query.all()
        total = len(developments)
        print(f"{total} gelisme yeniden cevrilecek.\n")
        failed = []
        for i, development in enumerate(developments, start=1):
            raw = development.raw_item
            try:
                title_tr, summary_tr = translate(raw.title, raw.summary)
                development.title_tr = title_tr
                development.summary_tr = summary_tr
                session.commit()
                print(f"[{i}/{total}] OK  #{development.id} {raw.title[:60]}")
            except Exception as e:
                session.rollback()
                failed.append(development.id)
                print(f"[{i}/{total}] HATA #{development.id}: {e}", file=sys.stderr)
            time.sleep(0.3)
        print(f"\nBitti. {total - len(failed)} basarili, {len(failed)} hata.")
        if failed:
            print(f"Hatali id'ler: {failed}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
