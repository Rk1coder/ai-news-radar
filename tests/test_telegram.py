from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_news_radar.models import Base, Development, RawItem, Source
from ai_news_radar.notifications import telegram


def make_development():
    source = Source(name='arxiv', source_type='academic')
    raw = RawItem(source=source, external_id='x', title='Original title',
                  url='https://example.com/news', summary='<p>Original summary.</p>')
    return Development(raw_item=raw, verified=True, priority_score=72,
                       title_tr='Görüntü analizinde yeni yöntem',
                       summary_tr='İlk kısa cümle. İkinci cümle. Üçüncü cümle.', sector_tags=['healthcare'])


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(telegram, 'TELEGRAM_ENABLED', True, raising=False)
    monkeypatch.setattr(telegram, 'TELEGRAM_BOT_TOKEN', 'test-secret')
    monkeypatch.setattr(telegram, 'TELEGRAM_CHAT_ID', '-100123')
    post = Mock(return_value=Mock(status_code=200, json=lambda: {'ok': True, 'result': {'message_id': 42}}))
    monkeypatch.setattr(telegram.requests, 'post', post)
    return post


@pytest.fixture
def sessions(tmp_path):
    engine = create_engine(f'sqlite:///{tmp_path / "telegram.db"}')
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def queued(sessions):
    with sessions() as session:
        development = make_development()
        session.add(development)
        session.flush()
        telegram.enqueue(session, development)
        session.commit()


def delivery(sessions):
    from ai_news_radar.models import TelegramDelivery
    with sessions() as session:
        return session.query(TelegramDelivery).one()


def test_message_is_short_translated_plain_text_with_original_link():
    dev = make_development()
    message = telegram._format_message(dev)
    assert 'Görüntü analizinde yeni yöntem' in message
    assert 'İlk kısa cümle. İkinci cümle.' in message
    assert 'Üçüncü' not in message
    assert dev.raw_item.url in message
    assert 'hype=' not in message
    dev.summary_tr = ''
    assert 'Original summary.' in telegram._format_message(dev)
    assert '<p>' not in telegram._format_message(dev)
    dev.title_tr = '😀' * 10000
    dev.summary_tr = '😀' * 10000
    assert len(telegram._format_message(dev).encode('utf-16-le')) // 2 <= 4096
    dev.raw_item.url = 'javascript:alert(1)'
    assert telegram._format_message(dev) is None


def test_queue_is_opt_in_verified_only_and_transactional(sessions, configured, monkeypatch):
    from ai_news_radar.models import TelegramDelivery
    with sessions() as session:
        dev = make_development()
        session.add(dev)
        session.flush()
        monkeypatch.setattr(telegram, 'TELEGRAM_ENABLED', False)
        telegram.enqueue(session, dev)
        assert session.query(TelegramDelivery).count() == 0
        monkeypatch.setattr(telegram, 'TELEGRAM_ENABLED', True)
        dev.verified = False
        telegram.enqueue(session, dev)
        assert session.query(TelegramDelivery).count() == 0
        dev.verified = True
        telegram.enqueue(session, dev)
        telegram.enqueue(session, dev)
        assert session.query(TelegramDelivery).count() == 1
        session.rollback()
        assert session.query(TelegramDelivery).count() == 0
    assert configured.call_count == 0


def test_sent_record_survives_restart_without_duplicate(sessions, configured):
    queued(sessions)
    assert telegram.publish_pending(sessions) == 'sent'
    assert delivery(sessions).message_id == 42
    assert telegram.publish_pending(sessions) == 'idle'
    assert configured.call_count == 1
    payload = configured.call_args.kwargs['json']
    assert payload['chat_id'] == '-100123'
    assert payload['link_preview_options']['is_disabled'] is True
    assert payload['disable_notification'] is True


def test_clear_rejection_defers_and_retries_after_telegram_delay(sessions, configured):
    queued(sessions)
    now = datetime.now(UTC) + timedelta(seconds=1)
    configured.return_value = Mock(status_code=429, json=lambda: {'ok': False, 'error_code': 429, 'parameters': {'retry_after': 120}})
    assert telegram.publish_pending(sessions, clock=lambda: now) == 'pending'
    assert telegram.publish_pending(sessions, clock=lambda: now + timedelta(seconds=30)) == 'idle'
    configured.return_value = Mock(status_code=200, json=lambda: {'ok': True, 'result': {'message_id': 43}})
    assert telegram.publish_pending(sessions, clock=lambda: now + timedelta(seconds=121)) == 'sent'
    assert configured.call_count == 2


def test_uncertain_timeout_is_not_automatically_repeated_or_logged_with_secret(sessions, configured, caplog):
    queued(sessions)
    configured.side_effect = requests.Timeout('https://api.telegram.org/bottest-secret/sendMessage')
    assert telegram.publish_pending(sessions) == 'unknown'
    assert telegram.publish_pending(sessions) == 'idle'
    assert configured.call_count == 1
    assert 'test-secret' not in caplog.text
    assert 'test-secret' not in delivery(sessions).last_error


def test_crashed_inflight_and_old_destination_are_not_resent(sessions, configured, monkeypatch):
    from ai_news_radar.models import TelegramDelivery
    queued(sessions)
    monkeypatch.setattr(telegram, 'TELEGRAM_CHAT_ID', '-100456')
    assert telegram.publish_pending(sessions) == 'idle'
    monkeypatch.setattr(telegram, 'TELEGRAM_CHAT_ID', '-100123')
    with sessions() as session:
        session.query(TelegramDelivery).one().status = 'sending'
        session.commit()
    assert telegram.publish_pending(sessions) == 'idle'
    assert delivery(sessions).status == 'unknown'
    assert configured.call_count == 0


def test_api_false_is_not_success_even_with_http_200(sessions, configured):
    queued(sessions)
    configured.return_value = Mock(status_code=200, json=lambda: {'ok': False, 'error_code': 403, 'description': 'private details'})
    assert telegram.publish_pending(sessions) == 'failed'
    assert delivery(sessions).message_id is None
    assert delivery(sessions).last_error == 'telegram_403'
    assert telegram.publish_pending(sessions) == 'idle'


def test_pipeline_queues_new_articles_but_never_backfills_existing_archive(sessions, configured):
    from ai_news_radar.models import TelegramDelivery
    from ai_news_radar.pipeline import run_pipeline
    from ai_news_radar.ingestion.base import FetchedItem
    from ai_news_radar.classification.llm_classifier import ClassificationResult
    class Connector:
        source_name = 'example-company'
        source_type = 'company'
        def fetch(self):
            return [FetchedItem(external_id='new', title='A new story', url='https://example.com/new', summary='Summary.', published_at=None)]
    with sessions() as session:
        session.add(make_development())
        session.commit()
        with patch('ai_news_radar.pipeline.classify', return_value=ClassificationResult(
            technical_impact_score=70, hype_score=40, applicability_score=60, sector_tags=['healthcare'], rationale='test'
        )):
            run_pipeline(session, [Connector()])
            run_pipeline(session, [Connector()])
        rows = session.query(TelegramDelivery).all()
        assert len(rows) == 1
        assert 'https://example.com/new' in rows[0].text
    assert configured.call_count == 0


def test_scheduler_delivers_when_scanning_disabled_and_after_scan_failure(monkeypatch):
    from ai_news_radar import scheduler, scans
    calls = []
    monkeypatch.setattr(telegram, 'publish_pending', lambda: calls.append('deliver'))
    monkeypatch.setattr(scheduler, 'AUTO_SCAN_ENABLED', False)
    monkeypatch.setattr(scans, 'run_scan', lambda **kwargs: calls.append('scan'))
    scheduler.run_cycle()
    assert calls == ['deliver']
    calls.clear()
    monkeypatch.setattr(scheduler, 'AUTO_SCAN_ENABLED', True)
    def failed(**kwargs):
        calls.append('scan')
        raise RuntimeError('private detail')
    monkeypatch.setattr(scans, 'run_scan', failed)
    scheduler.run_cycle()
    assert calls == ['scan', 'deliver']


def test_sender_uses_scan_lock_before_network_io(sessions, configured):
    from ai_news_radar.scans import scan_lock
    queued(sessions)
    with sessions() as session:
        with scan_lock(session.get_bind()) as acquired:
            assert acquired
            assert telegram.publish_pending(sessions) == 'busy'
    assert delivery(sessions).status == 'pending'
    assert configured.call_count == 0


def test_telegram_retry_delay_starts_after_response_arrives(sessions, configured):
    queued(sessions)
    start = datetime.now(UTC) + timedelta(seconds=1)
    configured.return_value = Mock(status_code=429, json=lambda: {'ok': False, 'error_code': 429, 'parameters': {'retry_after': 120}})
    with patch.object(telegram, 'datetime', wraps=datetime) as clock:
        clock.now.side_effect = [start, start + timedelta(seconds=10)]
        assert telegram.publish_pending(sessions) == 'pending'
    assert delivery(sessions).next_attempt_at == (start + timedelta(seconds=130)).replace(tzinfo=None)
