#!/bin/sh
set -eu
umask 077

backup_once() {
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  temporary="/backups/radar-$stamp.dump.partial"
  if pg_dump --format=custom --no-owner --no-acl --file="$temporary"; then
    mv "$temporary" "/backups/radar-$stamp.dump"
    # Retain one week; prune only after a successful new backup.
    find /backups -name 'radar-*.dump' -type f -mtime +7 -exec rm -f {} \;
    printf 'Backup saved: radar-%s.dump\n' "$stamp"
    return 0
  fi
  rm -f "$temporary"
  echo 'Backup failed; existing backups retained.' >&2
  return 1
}

if [ "${1:-}" = '--once' ]; then
  backup_once
  exit
fi
trap 'exit 0' TERM INT
while :; do
  if backup_once; then delay=86400; else delay=300; fi
  sleep "$delay" &
  wait $! || true
done
