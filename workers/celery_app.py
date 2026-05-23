from celery import Celery
from celery.schedules import crontab
from backend.app.config import settings

# Initialize Celery app
celery_app = Celery(
    "neuralpulse_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["workers.tasks"]
)

# Update Celery configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,  # 1 hour result expiration
)

# Automated crawler periodic schedules (run every 30 minutes)
celery_app.conf.beat_schedule = {
    "run-rss-ingestion-every-30-minutes": {
        "task": "workers.tasks.trigger_ingestion_task",
        "schedule": crontab(minute="*/30"),
        "args": ("all",),
    }
}

