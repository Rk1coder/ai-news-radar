"""Mevcut Development kayitlarinin title_tr/summary_tr alanlarini yeniden cevirir.

Skorlari/etiketleri degistirmez - sadece ceviriyi yeniler (duzeltilmis Turkce
yazim kurallarini uygulamak icin). Calistirma: python -m ai_news_radar.retranslate
"""

import sys
import time

from ai_news_radar.classification.llm_classifier import translate
from ai_news_radar.db import get_session
from ai_news_radar.models import Development


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    session = get_session()
    try:
        query = session.query(Development).order_by(Development.id)
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
