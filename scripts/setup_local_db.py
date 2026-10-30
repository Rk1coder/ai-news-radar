#!/usr/bin/env python3
"""Select persistent Compose PostgreSQL without deleting the old connection."""
import secrets
from pathlib import Path
from urllib.parse import quote, urlsplit

from dotenv import dotenv_values

from connect_proton import save_settings

ROOT = Path(__file__).resolve().parents[1]


def configure(path: Path):
    values = dotenv_values(path)
    previous = values.get('DATABASE_URL', '')
    password = values.get('POSTGRES_PASSWORD') or secrets.token_hex(32)
    settings = {
        'POSTGRES_PASSWORD': password,
        'DATABASE_URL': f'postgresql+psycopg2://radar:{quote(password, safe="")}@postgres:5432/radar',
        'COMPOSE_FILE': 'docker-compose.yml:docker-compose.local.yml',
    }
    if previous and urlsplit(previous).hostname != 'postgres':
        if values.get('PREVIOUS_DATABASE_URL') and values['PREVIOUS_DATABASE_URL'] != previous:
            raise ValueError('A different previous connection is already saved; refusing to overwrite it.')
        settings['PREVIOUS_DATABASE_URL'] = previous
    if values.get('EMAIL_SMTP_HOST') == 'hydroxide':
        profiles = set(filter(None, values.get('COMPOSE_PROFILES', '').split(',')))
        settings['COMPOSE_PROFILES'] = ','.join(sorted(profiles | {'proton'}))
    save_settings(path, settings)


if __name__ == '__main__':
    path = ROOT / '.env'
    if not path.exists():
        raise SystemExit('Önce .env.example dosyasını .env olarak kopyalayıp API bilgilerini doldur.')
    configure(path)
    print('Kalıcı PostgreSQL seçildi. Eski bağlantı varsa PREVIOUS_DATABASE_URL alanında korundu.')
    print('Haber aktarımı yapılmadı. Başlat: ./scripts/start.sh')
