"""Daily Radar digest: durable claim, complete MIME and Proton-compatible SMTP."""
import base64
import logging
import smtplib
import ssl
from datetime import UTC, datetime, timedelta
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import format_datetime, formataddr, make_msgid
from importlib.resources import files
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ai_news_radar.config import (
    EMAIL_ENABLED, EMAIL_FROM, EMAIL_RECIPIENTS, EMAIL_SEND_HOUR, EMAIL_SMTP_HOST,
    EMAIL_SMTP_PASSWORD, EMAIL_SMTP_PORT, EMAIL_SMTP_USER, EMAIL_SMTP_SECURITY,
    EMAIL_PUBLIC_URL, SCAN_TIMEZONE,
)
from ai_news_radar.models import Development, EmailDigestAttempt, EmailDigestLog, RawItem
from ai_news_radar.notifications.email_template import render_html as _render_html, render_text
from ai_news_radar.notifications.email_grouping import group_digest_stories

log = logging.getLogger(__name__)


def enabled():
    return bool(EMAIL_ENABLED and EMAIL_SMTP_HOST and EMAIL_SMTP_USER
                and EMAIL_SMTP_PASSWORD and EMAIL_FROM and EMAIL_RECIPIENTS)


def _local(now):
    return now.astimezone(ZoneInfo(SCAN_TIMEZONE))


def _today_str(now):
    return _local(now).strftime("%Y-%m-%d")


def due(session, now=None, *, force=False):
    now = now or datetime.now(UTC)
    if not enabled() or (not force and _local(now).hour < EMAIL_SEND_HOUR):
        return False
    day = _today_str(now)
    if session.query(EmailDigestLog).filter_by(sent_date=day).first():
        return False
    attempt = session.get(EmailDigestAttempt, day, populate_existing=True)
    return attempt is None or (attempt.status == "failed" and (
        attempt.next_attempt_at is None or attempt.next_attempt_at <= now.replace(tzinfo=None)))


def _top_stories(session, limit=12, *, now=None, grouping=None):
    if limit <= 0:
        return []
    now = (now or datetime.now(UTC)).astimezone(UTC).replace(tzinfo=None)
    since = now - timedelta(hours=24)
    rows = (session.query(Development).join(RawItem)
            .options(joinedload(Development.raw_item).joinedload(RawItem.source))
            .filter(Development.verified.is_(True))
            .filter(or_(and_(RawItem.published_at >= since, RawItem.published_at <= now),
                        and_(RawItem.published_at.is_(None), RawItem.fetched_at >= since, RawItem.fetched_at <= now)))
            .order_by(Development.priority_score.desc().nullslast(), RawItem.published_at.desc(), Development.id.asc()))
    stories, seen = [], set()
    for story in rows.yield_per(50):
        try:
            parts = urlsplit(story.raw_item.url or "")
            query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                     if not key.lower().startswith("utm_") and key.lower() not in ("fbclid", "gclid", "mc_cid", "mc_eid")]
            key = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(query), ""))
        except ValueError:
            key = f"invalid-url-story:{story.id}"
        if key in seen:
            continue
        seen.add(key)
        stories.append(story)
        if len(stories) >= 80:
            break
    # Select distinct events before applying the newsletter limit, so repeated
    # coverage cannot consume the available slots or hide lower-ranked events.
    return (grouping or group_digest_stories)(stories)[:limit]


def _logo_bytes():
    return files("ai_news_radar").joinpath("assets/radar-logo.png").read_bytes()


def build_message(stories, now, *, message_id=None):
    msg = MIMEMultipart("related")
    msg["Subject"] = f"Radar · Günlük AI Özeti · {_local(now):%d.%m.%Y}"
    msg["From"] = formataddr(("Radar", EMAIL_FROM))
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)
    msg["Date"] = format_datetime(now)
    msg["Message-ID"] = message_id or make_msgid(domain=EMAIL_FROM.rsplit("@", 1)[-1] or "radar.local")
    alternative = MIMEMultipart("alternative")
    label = _local(now).strftime("%d.%m.%Y")
    alternative.attach(MIMEText(render_text(stories, label, timezone=SCAN_TIMEZONE), "plain", "utf-8"))
    alternative.attach(MIMEText(_render_html(stories, label, timezone=SCAN_TIMEZONE, public_url=EMAIL_PUBLIC_URL), "html", "utf-8"))
    msg.attach(alternative)
    logo = MIMEImage(_logo_bytes(), _subtype="png")
    logo.add_header("Content-ID", "<radar-logo>")
    logo.add_header("Content-Disposition", "inline", filename="radar-logo.png")
    msg.attach(logo)
    return msg


def _claim(session, now):
    """Commit a unique daily claim before any SMTP I/O, including on first use."""
    day, stamp = _today_str(now), now.replace(tzinfo=None)
    attempt = session.get(EmailDigestAttempt, day)
    if attempt is None:
        attempt = EmailDigestAttempt(sent_date=day, status="sending", attempts=1,
                                     updated_at=stamp, message_id=make_msgid())
        session.add(attempt)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return None
    else:
        changed = session.execute(update(EmailDigestAttempt).where(
            EmailDigestAttempt.sent_date == day, EmailDigestAttempt.status == "failed",
            or_(EmailDigestAttempt.next_attempt_at.is_(None), EmailDigestAttempt.next_attempt_at <= stamp),
        ).values(status="sending", attempts=EmailDigestAttempt.attempts + 1, updated_at=stamp))
        session.commit()
        if changed.rowcount != 1:
            return None
    return session.get(EmailDigestAttempt, day, populate_existing=True)


def _failed(session, attempt, now, error, *, uncertain=False):
    attempt.status = "uncertain" if uncertain else "failed"
    attempt.last_error = error
    attempt.updated_at = now.replace(tzinfo=None)
    attempt.next_attempt_at = None if uncertain else (now + timedelta(minutes=5)).replace(tzinfo=None)
    session.commit()
    log.warning("Daily email %s: %s", attempt.status, error)


def send_daily_digest(session, now=None, *, force=False) -> bool:
    now = now or datetime.now(UTC)
    if not due(session, now, force=force):
        return False
    if EMAIL_SMTP_SECURITY == "local" and EMAIL_SMTP_HOST not in ("127.0.0.1", "localhost", "::1", "hydroxide"):
        log.warning("Local SMTP mode requires loopback or the private hydroxide sidecar")
        return False
    attempt = _claim(session, now)
    if attempt is None:
        return False
    transmitting, accepted = False, False
    try:
        stories = _top_stories(session, now=now)
        msg = build_message(stories, now, message_id=attempt.message_id)
        context = ssl.create_default_context()
        transport = smtplib.SMTP_SSL if EMAIL_SMTP_SECURITY == "ssl" else smtplib.SMTP
        options = {"timeout": 30}
        if EMAIL_SMTP_SECURITY == "ssl":
            options["context"] = context
        with transport(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT, **options) as smtp:
            if EMAIL_SMTP_SECURITY == "starttls":
                smtp.starttls(context=context)
            smtp.login(EMAIL_SMTP_USER, EMAIL_SMTP_PASSWORD)
            transmitting = True
            refused = smtp.sendmail(EMAIL_FROM, list(EMAIL_RECIPIENTS), msg.as_bytes())
            if isinstance(refused, dict) and refused:
                _failed(session, attempt, now, "PartialRecipientRefusal", uncertain=True)
                return False
            accepted = True
    except Exception as exc:
        if not accepted:
            explicit = isinstance(exc, (smtplib.SMTPResponseException, smtplib.SMTPRecipientsRefused))
            _failed(session, attempt, now, type(exc).__name__, uncertain=transmitting and not explicit)
            return False
        log.info("SMTP accepted email; connection ended during QUIT")
    attempt.status = "sent"
    attempt.last_error = ""
    attempt.updated_at = now.replace(tzinfo=None)
    session.add(EmailDigestLog(sent_date=_today_str(now), story_count=len(stories)))
    session.commit()
    return True


def main():
    import argparse
    from pathlib import Path
    from ai_news_radar.db import get_session, init_db

    parser = argparse.ArgumentParser(description="Radar günlük özet ve Proton SMTP")
    parser.add_argument("--send-now", action="store_true", help="Saati beklemeden gönderir; günlük tekrar korumasını korur")
    parser.add_argument("--preview", type=Path, help="Göndermeden HTML ve .eml önizlemesi kaydeder")
    args = parser.parse_args()
    now = datetime.now(UTC)
    if args.preview:
        with get_session() as session:
            stories = _top_stories(session, now=now)
            msg = build_message(stories, now)
            html = _render_html(stories, _local(now).strftime("%d.%m.%Y"), timezone=SCAN_TIMEZONE, public_url=EMAIL_PUBLIC_URL)
            html = html.replace("cid:radar-logo", "data:image/png;base64," + base64.b64encode(_logo_bytes()).decode())
            args.preview.parent.mkdir(parents=True, exist_ok=True)
            args.preview.write_text(html, encoding="utf-8")
            args.preview.with_suffix(".eml").write_bytes(msg.as_bytes())
            print(f"Önizleme hazır: {args.preview} ({len(stories)} haber). E-posta gönderilmedi.")
        return
    if not enabled():
        print("Gönderim kapalı: SMTP gönderen/alıcı ve köprü bağlantısı tamamlanmalı.")
        return
    init_db()
    with get_session() as session:
        if args.send_now:
            print("SMTP sunucusu kabul etti." if send_daily_digest(session, now, force=True)
                  else "Gönderilmedi. Günlük kayıt ve bağlantı durumunu kontrol et.")
        else:
            attempt = session.get(EmailDigestAttempt, _today_str(now))
            print(f"Günlük saat: {EMAIL_SEND_HOUR:02d}:00 ({SCAN_TIMEZONE}) · Bugün: {attempt.status if attempt else 'bekliyor'}")
            if attempt and attempt.status in ("sending", "uncertain"):
                print("Otomatik tekrar bekletiliyor. Yeniden göndermeden önce Proton Gönderilenler klasörünü kontrol et.")


if __name__ == "__main__":
    main()
