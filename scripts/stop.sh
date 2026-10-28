#!/usr/bin/env bash
# Uygulamayı durdurur (container'ları durdurup kaldırır; imajlar ve .env korunur).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose down

echo "Durduruldu. Tekrar başlatmak için: ./scripts/start.sh"
