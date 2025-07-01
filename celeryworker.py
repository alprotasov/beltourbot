import os
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

def make_celery():
    broker_url = os.getenv('CELERY_BROKER_URL', settings.CELERY_BROKER_URL)
    result_backend = os.getenv('CELERY_RESULT_BACKEND', settings.CELERY_RESULT_BACKEND)
    celery_app = Celery(
        'celeryworker',
        broker=broker_url,
        backend=result_backend,
        include=['celery_worker']
    )
    celery_app.conf.update(
        task_serializer='json',
        result_serializer='json',
        accept_content=['json'],
        timezone=settings.TIMEZONE,
        enable_utc=True
    )
    return celery_app

def schedule_tasks(celery_app):
    celery_app.conf.beat_schedule = {
        'send-daily-route-suggestions': {
            'task': 'celery_worker.send_daily_route_suggestions',
            'schedule': crontab(hour=9, minute=0),
            'args': []
        },
        'cleanup-expired-sessions': {
            'task': 'celery_worker.cleanup_expired_sessions',
            'schedule': crontab(hour=0, minute=0),
            'args': []
        },
        'send-weekly-summary': {
            'task': 'celery_worker.send_weekly_summary',
            'schedule': crontab(day_of_week='sun', hour=18, minute=0),
            'args': []
        }
    }

celery_app = make_celery()
schedule_tasks(celery_app)

if __name__ == "__main__":
    celery_app.start()