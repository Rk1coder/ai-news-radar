from ai_news_radar.db import get_session, init_db
from ai_news_radar.ingestion import default_connectors
from ai_news_radar.pipeline import run_pipeline
from ai_news_radar.scans import scan_lock


def main() -> None:
    init_db()
    session = get_session()
    try:
        with scan_lock(session.get_bind()) as acquired:
            if not acquired:
                print("Bir tarama zaten devam ediyor.")
                return
            developments = run_pipeline(session, default_connectors())
        print(f"{len(developments)} yeni gelisme islendi.\n")
        for development in sorted(
            developments, key=lambda d: d.priority_score or -1, reverse=True
        ):
            raw = development.raw_item
            if not development.verified:
                print(f"[DOGRULANAMADI] {raw.title}\n  {development.verification_notes}\n")
                continue
            print(
                f"[P{development.priority_score}] {raw.title}\n"
                f"  etki={development.technical_impact_score} "
                f"hype={development.hype_score} "
                f"uygulanabilirlik={development.applicability_score} "
                f"sektorler={development.sector_tags}\n"
                f"  {raw.url}\n"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
