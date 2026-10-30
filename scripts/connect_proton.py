#!/usr/bin/env python3
"""User-run interactive Proton login; never accepts the Proton password in chat."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ['docker', 'compose', '--profile', 'proton']


def _run(args, **kwargs):
    return subprocess.run(COMPOSE + args, cwd=ROOT, check=True, **kwargs)


def save_settings(path, settings):
    """Preserve unrelated secrets; replace the file atomically with mode 0600."""
    lines = path.read_text().splitlines() if path.exists() else []
    remaining = dict(settings)
    output = []
    for line in lines:
        key = line.split('=', 1)[0] if '=' in line and not line.lstrip().startswith('#') else None
        if key in settings:
            if key in remaining:
                output.append(key + '=' + json.dumps(remaining.pop(key), ensure_ascii=False))
        else:
            output.append(line)
    output.extend(key + '=' + json.dumps(value, ensure_ascii=False) for key, value in remaining.items())
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.proton-', delete=False) as handle:
        temporary = Path(handle.name)
        try:
            os.chmod(temporary, 0o600)
            handle.write('\n'.join(output) + '\n')
            handle.flush()
            os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description='Proton hesabını yerelde bağlar; otomatik günlük gönderimi açmaz.')
    parser.add_argument('--account', required=True, help='Gönderen Proton hesabı')
    parser.add_argument('--recipient', help='Deneme alıcısı; belirtilmezse kendi hesabın')
    parser.add_argument('--send-test', action='store_true', help='Bağlantıdan sonra alıcıya bir günlük özet gönderir')
    args = parser.parse_args()
    recipient = args.recipient or args.account
    for address in (args.account, recipient):
        if not re.fullmatch(r'[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+', address):
            parser.error('Geçerli gönderen ve alıcı adresleri gerekli.')
    if not sys.stdin.isatty():
        parser.error('Bu komutu kendi etkileşimli terminalinde çalıştır. Proton parolanı sohbete yazma.')
    print('Proton parolanı yalnızca aşağıdaki Password alanına gir. Hesap doğrulaması Proton ile hydroxide arasında yapılır.')
    _run(['stop', 'hydroxide'])
    try:
        _run(['run', '--rm', 'hydroxide', 'auth', args.account])
    finally:
        _run(['up', '-d', 'hydroxide'])
    bridge = getpass.getpass('Yukarıdaki Bridge password değerini buraya yapıştır (gizli): ').strip()
    if not bridge or '\n' in bridge or len(bridge) > 256:
        parser.error('Köprü parolası eksik veya geçersiz. Proton giriş parolanı kullanma.')
    # Pass the generated bridge password over stdin, never in process arguments.
    verify = '''import json,smtplib,sys
data=json.load(sys.stdin)
try:
    with smtplib.SMTP('hydroxide',1025,timeout=30) as smtp:
        smtp.login(data['user'],data['password'])
except Exception as exc:
    print('Köprü bağlantısı doğrulanamadı: '+type(exc).__name__)
    sys.exit(1)
print('Proton SMTP bağlantısı doğrulandı.')
'''
    # This probe works when the application is stopped and never accesses the database.
    _run(['run', '--rm', '--no-deps', '-T', '-e', 'EMAIL_ENABLED=false',
          '-e', 'TELEGRAM_ENABLED=false', 'scheduler', 'python', '-c', verify],
         input=json.dumps({'user': args.account, 'password': bridge}), text=True)
    settings = {
        'EMAIL_ENABLED': 'false', 'EMAIL_SMTP_HOST': 'hydroxide', 'EMAIL_SMTP_PORT': '1025',
        'EMAIL_SMTP_SECURITY': 'local', 'EMAIL_SMTP_USER': args.account,
        'EMAIL_SMTP_PASSWORD': bridge, 'EMAIL_FROM': args.account,
        'EMAIL_RECIPIENTS': recipient, 'EMAIL_SEND_HOUR': '16',
    }
    save_settings(ROOT / '.env', settings)
    print('Bağlantı yerelde kaydedildi. Otomatik günlük gönderim kapalı.')
    if args.send_test:
        print(f'Tek günlük özet denemesi gönderiliyor: {recipient}')
        send = '''import sys
from ai_news_radar.db import get_session,init_db
from ai_news_radar.notifications.email import send_daily_digest
init_db()
with get_session() as session:
    sent=send_daily_digest(session,force=True)
print('SMTP sunucusu test e-postasını kabul etti. Gelen kutunu kontrol et.' if sent else 'Test gönderilmedi; günlük kayıt veya bağlantı durumunu kontrol et.')
sys.exit(0 if sent else 1)
'''
        _run(['run', '--rm', '--no-deps', '-T', '-e', 'EMAIL_ENABLED=true',
              'scheduler', 'python', '-c', send], env={**os.environ, **settings})


if __name__ == '__main__':
    try:
        main()
    except (subprocess.CalledProcessError, KeyboardInterrupt):
        print('\nBağlantı adımı tamamlanmadı. Otomatik gönderim açılmadı.', file=sys.stderr)
        sys.exit(1)
