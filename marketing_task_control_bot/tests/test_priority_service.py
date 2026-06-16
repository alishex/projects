from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.priority_service import calculate_task_score, sort_tasks

TZ = ZoneInfo("Asia/Tashkent")
NOW = datetime(2026, 5, 29, 12, 0, tzinfo=TZ)


def task(priority="P4", deadline=None, status="ACTIVE", created_at=None):
    return {
        "priority": priority,
        "final_deadline": (deadline or (NOW + timedelta(days=10))).isoformat(),
        "status": status,
        "created_at": (created_at or NOW).isoformat(),
    }


def test_priority_base_points_are_correct():
    far = NOW + timedelta(days=10)
    assert calculate_task_score(task("P1", far), NOW, TZ) == 400
    assert calculate_task_score(task("P2", far), NOW, TZ) == 300
    assert calculate_task_score(task("P3", far), NOW, TZ) == 200
    assert calculate_task_score(task("P4", far), NOW, TZ) == 100


def test_overdue_receives_highest_bonus():
    assert calculate_task_score(task("P4", NOW - timedelta(hours=1), "OVERDUE"), NOW, TZ) == 1100


def test_deadline_closeness_affects_score():
    assert calculate_task_score(task("P1", NOW + timedelta(hours=12)), NOW, TZ) == 480
    assert calculate_task_score(task("P1", NOW + timedelta(days=2)), NOW, TZ) == 450
    assert calculate_task_score(task("P1", NOW + timedelta(days=6)), NOW, TZ) == 420


def test_equal_score_uses_nearest_deadline():
    later = task("P1", NOW + timedelta(hours=20), created_at=NOW - timedelta(days=2))
    sooner = task("P1", NOW + timedelta(hours=10), created_at=NOW - timedelta(days=1))
    assert sort_tasks([later, sooner], NOW, TZ)[0] is sooner


def test_equal_score_and_deadline_uses_oldest_task():
    deadline = NOW + timedelta(days=10)
    newer = task("P1", deadline, created_at=NOW - timedelta(days=1))
    older = task("P1", deadline, created_at=NOW - timedelta(days=2))
    assert sort_tasks([newer, older], NOW, TZ)[0] is older
