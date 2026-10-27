"""Compact Telegram news with a durable outbox. No network I/O during ingestion."""
import argparse
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import requests
from sqlalchemy import func

from ai_news_radar.config import TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from ai_news_radar.db import get_session
from ai_news_radar.models import Development, TelegramDelivery

log = logging.getLogger(__name__)
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def enabled():
    return bool(TELEGRAM_ENABLED and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


class _PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        elif tag in ('p', 'br', 'div', 'li'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _compact(value, limit):
    parser = _PlainText()
    parser.feed(value or '')
    text = re.sub(r'\s+', ' ', ''.join(parser.parts)).strip()
    if len(text) > limit:
        text = text[:limit - 1].rsplit(' ', 1)[0] + '…'
    return text


def _format_message(development: Development) -> str | None:
    raw = development.raw_item
    url = (raw.url or '').strip()
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in ('http', 'https') or not parsed.netloc
                or any(c.isspace() or ord(c) < 32 for c in url)
                or len(url.encode('utf-16-le')) // 2 > 2000):
            return None
    except ValueError:
        return None
    title = _compact(development.title_tr or raw.title, 180)
    summary = _compact(development.summary_tr or raw.summary, 320)
    summary = ' '.join(re.split(r'(?<=[.!?])\s+', summary)[:2])
    source = _compact(raw.source.name.replace('-', ' '), 60)
    date = ''
    if raw.published_at:
        published = raw.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=UTC)
        date = published.astimezone(ZoneInfo('Europe/Istanbul')).strftime(' · %d.%m.%Y')
    return f'📰 {title}\n\n{summary or "Ayrıntılar kaynak bağlantısında."}\n\n{source}{date}\n🔗 {url}'


def enqueue(session, development):
    """Call inside the source transaction, after the development has its ID."""
    if not enabled() or not development.verified:
        return
    message = _format_message(development)
    if not message:
        log.warning('Telegram queue skipped development %s: invalid source URL', development.id)
        return
    if session.query(TelegramDelivery.id).filter_by(development_id=development.id, chat_id=TELEGRAM_CHAT_ID).first():
        return
    session.add(TelegramDelivery(development_id=development.id, chat_id=TELEGRAM_CHAT_ID, text=message))


def publish_pending(session_factory=get_session, *, clock=None):
    """One message per scheduler tick. Never retry an ambiguous send automatically."""
    if not enabled():
        return 'disabled'
    # Local import avoids the pipeline -> outbox -> scans -> pipeline cycle.
    from ai_news_radar.scans import scan_lock
    clock = clock or (lambda: datetime.now(UTC))
    now = clock()
    with session_factory() as session:
        with scan_lock(session.get_bind()) as acquired:
            if not acquired:
                return 'busy'
            # An abandoned 'sending' row may already have reached Telegram.
            session.query(TelegramDelivery).filter_by(chat_id=TELEGRAM_CHAT_ID, status='sending').update(
                {'status': 'unknown', 'last_error': 'interrupted_send'}, synchronize_session=False)
            session.commit()
            row = session.query(TelegramDelivery).filter_by(chat_id=TELEGRAM_CHAT_ID, status='pending').order_by(TelegramDelivery.id).first()
            if row is None:
                return 'idle'
            due = row.next_attempt_at.replace(tzinfo=UTC) if row.next_attempt_at.tzinfo is None else row.next_attempt_at
            if due > now:
                return 'idle'  # Keep FIFO order and honour a chat-wide flood delay.
            row.status = 'sending'
            row.attempts += 1
            session.commit()
            try:
                response = requests.post(
                    TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN),
                    json={'chat_id': row.chat_id, 'text': row.text,
                          'link_preview_options': {'is_disabled': True}, 'disable_notification': True},
                    timeout=(5, 15), allow_redirects=False,
                )
                received_at = clock()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError('invalid response')
                result = data.get('result')
                message_id = result.get('message_id') if isinstance(result, dict) else None
                if response.status_code == 200 and data.get('ok') is True and type(message_id) is int:
                    row.status, row.message_id, row.sent_at, row.last_error = 'sent', message_id, received_at, ''
                elif data.get('ok') is False and type(data.get('error_code')) is int:
                    code = data['error_code']
                    row.last_error = f'telegram_{code}'
                    if code == 429 or 500 <= code < 600:
                        params = data.get('parameters') or {}
                        delay = params.get('retry_after', 300) if isinstance(params, dict) else 300
                        delay = max(30, delay) if type(delay) is int else 300
                        row.status, row.next_attempt_at = 'pending', received_at + timedelta(seconds=delay)
                    else:
                        row.status = 'failed'
                else:
                    row.status, row.last_error = 'unknown', 'invalid_response'
            except (requests.RequestException, ValueError):
                # URLs in request exceptions contain the bot token: never log them.
                row.status, row.last_error = 'unknown', 'transport_or_response_error'
            session.commit()
            log.info('Telegram delivery %s: %s', row.id, row.status)
            return row.status


def main():
    """Local diagnostics only; neither command sends nor queues anything."""
    parser = argparse.ArgumentParser(description='Telegram yerel önizleme ve durum (mesaj göndermez)')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    with get_session() as session:
        if args.preview:
            latest = session.query(Development).filter_by(verified=True).order_by(Development.id.desc()).first()
            print(_format_message(latest) if latest else 'Önizleme için haber bulunamadı.')
        else:
            counts = dict(session.query(TelegramDelivery.status, func.count(TelegramDelivery.id)).filter_by(chat_id=TELEGRAM_CHAT_ID).group_by(TelegramDelivery.status).all())
            print(json.dumps({'enabled': TELEGRAM_ENABLED, 'configured': bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID), 'queue': counts}))


if __name__ == '__main__':
    main()
