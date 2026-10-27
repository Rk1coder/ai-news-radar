from unittest.mock import Mock, patch

from ai_news_radar.scheduler import run_cycle


def test_run_cycle_skips_scan_when_disabled_but_still_publishes():
    with patch("ai_news_radar.scans.run_scan") as run_scan, \
         patch("ai_news_radar.notifications.telegram.publish_pending") as publish_pending:
        run_cycle(auto_scan_enabled=False, interval_minutes=15)
    run_scan.assert_not_called()
    publish_pending.assert_called_once()


def test_run_cycle_runs_scan_when_enabled_and_then_publishes():
    with patch("ai_news_radar.scans.run_scan", return_value={"id": 1, "status": "succeeded", "new_count": 2}) as run_scan, \
         patch("ai_news_radar.notifications.telegram.publish_pending") as publish_pending:
        run_cycle(auto_scan_enabled=True, interval_minutes=15)
    run_scan.assert_called_once()
    publish_pending.assert_called_once()


def test_run_cycle_uses_module_default_when_auto_scan_enabled_not_given():
    with patch("ai_news_radar.scheduler.AUTO_SCAN_ENABLED", False), \
         patch("ai_news_radar.scans.run_scan") as run_scan, \
         patch("ai_news_radar.notifications.telegram.publish_pending"):
        run_cycle(interval_minutes=15)
    run_scan.assert_not_called()


def test_run_cycle_swallows_scan_exception_and_still_publishes():
    with patch("ai_news_radar.scans.run_scan", side_effect=RuntimeError("db exploded")), \
         patch("ai_news_radar.notifications.telegram.publish_pending") as publish_pending:
        run_cycle(auto_scan_enabled=True, interval_minutes=15)
    publish_pending.assert_called_once()


def test_run_cycle_swallows_publish_exception():
    with patch("ai_news_radar.scans.run_scan", return_value=None), \
         patch("ai_news_radar.notifications.telegram.publish_pending", side_effect=RuntimeError("network down")):
        run_cycle(auto_scan_enabled=True, interval_minutes=15)  # must not raise


def test_run_cycle_does_not_log_failure_when_scan_result_is_falsy():
    with patch("ai_news_radar.scans.run_scan", return_value=None) as run_scan, \
         patch("ai_news_radar.notifications.telegram.publish_pending") as publish_pending:
        run_cycle(auto_scan_enabled=True, interval_minutes=0)
    run_scan.assert_called_once()
    publish_pending.assert_called_once()
