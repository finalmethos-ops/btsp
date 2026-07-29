from app.services.system_health_service import _metric_severity


def test_metric_severity_thresholds():
    assert _metric_severity("queued_notifications", 0) == "info"
    assert _metric_severity("queued_notifications", 99) == "warning"
    assert _metric_severity("queued_notifications", 100) == "critical"
    assert _metric_severity("stale_queued_notifications", 1) == "critical"
    assert _metric_severity("overdue_event_staff_tasks", 9) == "warning"
    assert _metric_severity("overdue_event_staff_tasks", 10) == "critical"
