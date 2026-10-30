#!/usr/bin/env bash
# Export a consistent snapshot to a private host directory, without stopping Radar.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
umask 077
mkdir -p backups
target="backups/radar-$(date -u +%Y%m%dT%H%M%SZ)-$$.dump"
trap 'rm -f "$target.partial"' EXIT
docker compose exec -T postgres pg_dump -U radar -d radar --format=custom --no-owner --no-acl > "$target.partial"
mv "$target.partial" "$target"
echo "Yedek kaydedildi: $target"
