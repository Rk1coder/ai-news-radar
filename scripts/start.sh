#!/usr/bin/env bash
# Uygulamayı tek komutla ayağa kaldırır: docker compose up -d --build.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env ]; then
  echo "'.env' bulunamadı, '.env.example'dan oluşturuluyor..."
  cp .env.example .env
  echo "'.env' dosyasında API/Telegram/SMTP bilgilerini doldurun; ardından .venv/bin/python scripts/setup_local_db.py komutunu çalıştırın."
  exit 1
fi

docker compose up -d --build

echo
echo "Arayüz:  http://localhost:3000"
echo "API:     http://localhost:8008"
echo "Durum:   docker compose ps"
echo "Loglar:  docker compose logs -f"
echo "Durdur:  ./scripts/stop.sh"
