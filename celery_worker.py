from celery import Celery
from celery.schedules import crontab
from app.config import settings

def make_celery():
    celery_app = Celery(
        __name__,
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=settings.TIMEZONE,
        enable_utc=True,
        task_track_started=True,
        task_default_retry_delay=60,
        task_max_retries=3,
    )
    return celery_app

celery_app = make_celery()

def register_tasks(celery):
    @celery.task(bind=True, name=f"{__name__}.send_daily_facts", default_retry_delay=60, max_retries=3)
    def send_daily_facts(self):
        try:
            from app.services.fact_service import run_daily_facts
            run_daily_facts()
        except Exception as exc:
            raise self.retry(exc=exc)

    @celery.task(bind=True, name=f"{__name__}.generate_qr_codes_batch", default_retry_delay=60, max_retries=3)
    def generate_qr_codes_batch(self):
        try:
            from app.services.qr_service import run_qr_generation
            run_qr_generation()
        except Exception as exc:
            raise self.retry(exc=exc)

    @celery.task(bind=True, name=f"{__name__}.send_bulk_notifications", default_retry_delay=60, max_retries=3)
    def send_bulk_notifications(self):
        try:
            from app.services.notification_service import run_bulk_notifications
            run_bulk_notifications()
        except Exception as exc:
            raise self.retry(exc=exc)

register_tasks(celery_app)

def schedule_daily_facts(celery):
    celery.conf.beat_schedule['daily-facts'] = {
        'task': f"{__name__}.send_daily_facts",
        'schedule': crontab(hour=8, minute=0),
    }

def schedule_qr_generation(celery):
    celery.conf.beat_schedule['generate-qr-codes-batch'] = {
        'task': f"{__name__}.generate_qr_codes_batch",
        'schedule': crontab(hour=2, minute=0),
    }

def schedule_bulk_notifications(celery):
    celery.conf.beat_schedule['send-bulk-notifications'] = {
        'task': f"{__name__}.send_bulk_notifications",
        'schedule': crontab(minute='*/15'),
    }

def setup_schedules(celery):
    celery.conf.beat_schedule = {}
    schedule_daily_facts(celery)
    schedule_qr_generation(celery)
    schedule_bulk_notifications(celery)

setup_schedules(celery_app)