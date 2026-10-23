# AI News Radar

AI/yakın teknoloji gelişmelerini tarayan, doğrulayan, sınıflandıran ve
önceliklendiren pipeline'ın MVP iskeleti. Yöntem ve alternatif kararların
gerekçeleri için bkz. proje planı.

## Mimari (Karar 4-A: modüler batch pipeline)

```
ingestion/   -> Karar 1-A: kaynak-özel connector (şimdilik arXiv)
verification/ -> Karar 2: kaynak türüne göre değişen doğrulama eşiği
classification/ -> Karar 3-B: LLM tabanlı üç eksenli skorlama
pipeline.py  -> toplama -> doğrulama -> sınıflandırma -> DB
cli.py       -> tek seferlik çalıştırma + öncelik sırasına göre çıktı
web/         -> Karar: çıktı formatı -> filtrelenebilir dashboard (FastAPI + Jinja2)
```

## Kurulum

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env   # ANTHROPIC_API_KEY'i doldur
docker compose up -d   # Postgres
```

## Çalıştırma

```bash
.venv/bin/python -m ai_news_radar.cli          # pipeline'ı bir kez çalıştır
.venv/bin/uvicorn ai_news_radar.web.app:app --reload --port 8000  # dashboard
```

## Test

```bash
.venv/bin/python -m pytest
```

Testler ağ çağrısı yapmaz (arXiv API ve Anthropic çağrıları mock'lanır) ve
Postgres gerektirmez (sqlite in-memory kullanılır).

## Durum / Sonraki Adımlar

Şu an sadece `arxiv` connector'ı (academic, tek-kaynak-yeterli) devrede.
Sosyal medya ve savunma sanayii kaynakları eklendiğinde, `verification/rules.py`
içindeki çapraz doğrulama mantığı (Karar 2-B/C: embedding clustering ve/veya
LLM fact-check) devreye alınmalı — şu an bu kaynak türleri `pending_cross_verification`
olarak işaretlenip sınıflandırmaya girmiyor.

Çıktı formatı sırası: dashboard (tamamlandı) -> Telegram bot bildirimi -> mail
özeti -> (gerekirse) WhatsApp. Dashboard ana arayüz; diğer kanallar bunun
üzerine eklenecek bildirim katmanları olacak.
