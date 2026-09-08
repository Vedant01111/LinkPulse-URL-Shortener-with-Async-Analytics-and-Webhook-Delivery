from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "linkpulse",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.click_tasks", "app.tasks.webhook_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Don't let a stuck task hold a worker forever
    task_time_limit=30,
    task_soft_time_limit=20,
)
