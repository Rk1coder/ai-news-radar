from datetime import UTC, datetime, timedelta
from email import message_from_bytes
import smtplib
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_news_radar.models import Base, Development, RawItem, Source
from ai_news_radar.notifications import email


def make_development(title="<script>alert(1)</script> New model"):
    source = Source(name="arxiv", source_type="academic")
    raw = RawItem(source=source, external_id="x", title="Original", url="https://example.com/a",
                  summary="Original summary.")
    return Development(raw_item=raw, verified=True, priority_score=70, classification_rationale="Yeni model yerel dağıtımı kolaylaştırıyor.",
                        title_tr=title, summary_tr="Özet metni.", sector_tags=["healthcare"])


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(email, "EMAIL_ENABLED", True, raising=False)
    monkeypatch.setattr(email, "EMAIL_SMTP_HOST", "127.0.0.1", raising=False)
    monkeypatch.setattr(email, "EMAIL_SMTP_USER", "radar@example.com", raising=False)
    monkeypatch.setattr(email, "EMAIL_SMTP_PASSWORD", "secret", raising=False)
    monkeypatch.setattr(email, "EMAIL_FROM", "radar@example.com", raising=False)
    monkeypatch.setattr(email, "EMAIL_RECIPIENTS", ("me@example.com",), raising=False)
    monkeypatch.setattr(email, "EMAIL_SEND_HOUR", 8, raising=False)
    monkeypatch.setattr(email, "SCAN_TIMEZONE", "UTC", raising=False)
    monkeypatch.setattr(email, "EMAIL_SMTP_SECURITY", "starttls", raising=False)


@pytest.fixture
def sessions(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'email.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_disabled_without_full_config():
    assert email.enabled() is False


def test_due_only_after_send_hour_and_only_once_per_day(configured, sessions):
    before_hour = datetime(2026, 1, 1, 7, 59, tzinfo=UTC)
    after_hour = datetime(2026, 1, 1, 8, 1, tzinfo=UTC)
    with sessions() as session:
        assert email.due(session, before_hour) is False
        assert email.due(session, after_hour) is True
        with patch.object(email.smtplib, "SMTP") as smtp:
            smtp.return_value.__enter__.return_value = MagicMock()
            assert email.send_daily_digest(session, after_hour) is True
        assert email.due(session, after_hour) is False
        next_day = datetime(2026, 1, 2, 9, 0, tzinfo=UTC)
        assert email.due(session, next_day) is True


def test_untranslated_html_is_escaped_so_a_title_cannot_inject_markup():
    html = email._render_html([make_development()], "01.01.2026")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_failed_send_does_not_log_as_sent_so_it_retries_next_cycle(configured, sessions):
    after_hour = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    with sessions() as session:
        with patch.object(email.smtplib, "SMTP") as smtp:
            smtp.side_effect = OSError("connection refused")
            assert email.send_daily_digest(session, after_hour) is False
        assert email.due(session, after_hour) is False
        assert email.due(session, after_hour + timedelta(minutes=6)) is True


def test_no_stories_still_sends_a_graceful_digest(configured, sessions):
    with sessions() as session:
        with patch.object(email.smtplib, "SMTP") as smtp:
            smtp.return_value.__enter__.return_value = MagicMock()
            assert email.send_daily_digest(session, datetime(2026, 1, 1, 8, 0, tzinfo=UTC)) is True
    assert "bulunamadı" in email._render_html([], "01.01.2026")


def test_selects_recent_publications_not_old_articles_fetched_today(sessions):
    now = datetime(2026, 10, 28, 13, tzinfo=UTC)
    with sessions() as session:
        source=Source(name='digest-fixture',source_type='company')
        for i, (published, fetched, verified, url) in enumerate([
            (now-timedelta(hours=2),now,True,'https://example.com/new'),
            (now-timedelta(days=10),now,True,'https://example.com/old'),
            (now+timedelta(hours=2),now,True,'https://example.com/future'),
            (None,now-timedelta(hours=3),True,'https://example.com/undated'),
            (now,now,False,'https://example.com/unverified'),
            (now,now,True,'https://example.com/new?utm_source=duplicate'),
        ]):
            d=make_development(f'Story {i}')
            d.priority_score=70-i
            d.raw_item.source=source
            d.raw_item.external_id=str(i)
            d.raw_item.published_at=published.replace(tzinfo=None) if published else None
            d.raw_item.fetched_at=fetched.replace(tzinfo=None)
            d.raw_item.url=url
            d.verified=verified
            session.add(d)
        session.commit()
        stories=email._top_stories(session,now=now,grouping=lambda rows:rows)
        assert {d.title_tr for d in stories}=={'Story 0','Story 3'}


def test_complete_message_has_plain_html_date_message_id_and_inline_logo():
    msg=email.build_message([make_development()],datetime(2026,10,28,13,tzinfo=UTC))
    parsed=message_from_bytes(msg.as_bytes())
    assert parsed['Message-ID'] and parsed['Date']
    assert {'text/plain','text/html','image/png'} <= {part.get_content_type() for part in parsed.walk()}
    html=next(p.get_payload(decode=True).decode() for p in parsed.walk() if p.get_content_type()=='text/html')
    logo = next(p for p in parsed.walk() if p.get_filename() == 'radar-logo.png')
    cid = logo['Content-ID'].strip('<>')
    assert '@' in cid
    assert 'cid:' + cid in html
    assert 'Neden önemli' in html


def test_unsafe_link_cannot_become_a_clickable_email_url():
    story=make_development()
    story.raw_item.url='javascript:alert(1)'
    assert 'href="javascript:' not in email._render_html([story],'28.10.2026')


def test_hydroxide_local_mode_avoids_starttls_and_uses_bridge_login(configured,monkeypatch,sessions):
    monkeypatch.setattr(email,'EMAIL_SMTP_SECURITY','local',raising=False)
    with sessions() as session,patch.object(email.smtplib,'SMTP') as smtp:
        assert email.send_daily_digest(session,datetime(2026,10,28,16,tzinfo=UTC))
        relay=smtp.return_value.__enter__.return_value
        relay.starttls.assert_not_called()
        relay.login.assert_called_once_with('radar@example.com','secret')


def test_local_mode_refuses_remote_plaintext_credentials(configured,monkeypatch,sessions):
    monkeypatch.setattr(email,'EMAIL_SMTP_SECURITY','local',raising=False)
    monkeypatch.setattr(email,'EMAIL_SMTP_HOST','smtp.example.com')
    with sessions() as session,patch.object(email.smtplib,'SMTP') as smtp:
        assert not email.send_daily_digest(session,datetime(2026,10,28,16,tzinfo=UTC))
        smtp.assert_not_called()


def test_ambiguous_smtp_disconnect_is_held_instead_of_automatically_duplicated(configured,sessions):
    now=datetime(2026,10,28,16,tzinfo=UTC)
    with sessions() as session,patch.object(email.smtplib,'SMTP') as smtp:
        smtp.return_value.__enter__.return_value.sendmail.side_effect=smtplib.SMTPServerDisconnected('lost after DATA')
        assert not email.send_daily_digest(session,now)
        assert not email.due(session,now+timedelta(hours=1))
        assert not email.send_daily_digest(session,now+timedelta(hours=1))
        assert smtp.call_count==1


def test_explicit_smtp_rejection_retries_after_backoff_without_logging_success(configured,sessions):
    now=datetime(2026,10,28,16,tzinfo=UTC)
    with sessions() as session,patch.object(email.smtplib,'SMTP') as smtp:
        smtp.return_value.__enter__.return_value.sendmail.side_effect=smtplib.SMTPDataError(451,b'try later')
        assert not email.send_daily_digest(session,now)
        assert not email.due(session,now+timedelta(seconds=30))
        assert email.due(session,now+timedelta(minutes=6))


def test_nested_sender_cannot_send_the_same_day_while_first_attempt_is_in_flight(configured,sessions):
    now=datetime(2026,10,28,16,tzinfo=UTC)
    def nested(*args):
        with sessions() as second:
            assert not email.due(second,now)
            assert not email.send_daily_digest(second,now)
        return {}
    with sessions() as session,patch.object(email.smtplib,'SMTP') as smtp:
        smtp.return_value.__enter__.return_value.sendmail.side_effect=nested
        assert email.send_daily_digest(session,now)
        assert smtp.call_count==1


def test_send_now_bypasses_hour_but_never_deletes_daily_send_history(configured,sessions):
    now=datetime(2026,10,28,1,tzinfo=UTC)
    with sessions() as session,patch.object(email.smtplib,'SMTP') as smtp:
        assert email.send_daily_digest(session,now,force=True)
        assert not email.send_daily_digest(session,now,force=True)
        assert smtp.call_count==1


def test_distinct_query_articles_survive_and_a_malformed_link_cannot_break_digest(sessions):
    now=datetime(2026,10,28,13,tzinfo=UTC)
    with sessions() as session:
        source=Source(name='query-news',source_type='company')
        for i,url in enumerate(['https://publisher.example/?p=101','https://publisher.example/?p=102','https://[broken']):
            story=make_development(f'Query {i}')
            story.raw_item.source=source
            story.raw_item.external_id=str(i)
            story.raw_item.url=url
            story.raw_item.published_at=now.replace(tzinfo=None)
            session.add(story)
        session.commit()
        stories=email._top_stories(session,now=now,grouping=lambda rows:rows)
        assert len(stories)==3
        assert email._render_html(stories,'28.10.2026')


def test_daily_16_istanbul_gate_uses_utc_clock(configured,monkeypatch,sessions):
    monkeypatch.setattr(email,'SCAN_TIMEZONE','Europe/Istanbul')
    monkeypatch.setattr(email,'EMAIL_SEND_HOUR',16)
    with sessions() as session:
        assert not email.due(session,datetime(2026,10,28,12,59,tzinfo=UTC))
        assert email.due(session,datetime(2026,10,28,13,0,tzinfo=UTC))


def test_failed_quit_after_data_acceptance_does_not_duplicate(configured,sessions):
    now=datetime(2026,10,28,16,tzinfo=UTC)
    with sessions() as session,patch.object(email.smtplib,'SMTP') as smtp:
        smtp.return_value.__exit__.side_effect=smtplib.SMTPServerDisconnected('QUIT lost')
        assert email.send_daily_digest(session,now)
        assert not email.send_daily_digest(session,now)
        assert smtp.call_count==1
