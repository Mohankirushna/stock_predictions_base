"""Celery() construction and Celery() itself don't connect to the broker,
so this is a pure config test — no live Redis required."""
from app.infrastructure.tasks.celery_app import celery_app
from app.infrastructure.tasks.schedule import beat_schedule, task_routes


def test_registered_task_names_are_routed() -> None:
    for entry in beat_schedule.values():
        task_name = entry["task"]
        prefix = task_name.split(".")[0]
        assert f"{prefix}.*" in task_routes, f"{task_name} has no matching queue route"


def test_beat_schedule_entries_reference_real_tasks() -> None:
    # Forces import of the task modules (registers them on celery_app).
    import app.infrastructure.tasks.ai_tasks  # noqa: F401
    import app.infrastructure.tasks.analysis_tasks  # noqa: F401
    import app.infrastructure.tasks.data_tasks  # noqa: F401

    for entry in beat_schedule.values():
        assert entry["task"] in celery_app.tasks


def test_data_analysis_and_ai_queues_are_distinct() -> None:
    queues = {task_routes["data.*"]["queue"], task_routes["analysis.*"]["queue"], task_routes["ai.*"]["queue"]}
    assert len(queues) == 3


def test_celery_app_uses_configured_redis_broker() -> None:
    from app.core.config import get_settings

    assert celery_app.conf.broker_url == get_settings().redis.url


def test_task_acks_late_and_no_prefetch_burst() -> None:
    # Long-running agent tasks shouldn't be prefetched in bulk or acked
    # before completion — a crashed worker should redeliver the task.
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
