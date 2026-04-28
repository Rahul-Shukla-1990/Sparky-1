from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings
from app.db import SessionLocal
from app.services.pipeline import run_collection_cycle
from app.services.telegram import poll_telegram_once

scheduler = BackgroundScheduler()


def scheduled_collection_job():
    db = SessionLocal()
    try: run_collection_cycle(db)
    finally: db.close()


def scheduled_telegram_job():
    if not settings.telegram_polling_enabled: return
    db = SessionLocal()
    try: poll_telegram_once(db)
    finally: db.close()


def start_scheduler():
    if not settings.scheduler_enabled: return
    scheduler.add_job(scheduled_collection_job, "interval", minutes=settings.collection_interval_minutes, id="collection_cycle", replace_existing=True)
    if settings.telegram_polling_enabled:
        scheduler.add_job(scheduled_telegram_job, "interval", minutes=settings.telegram_polling_interval_minutes, id="telegram_polling", replace_existing=True)
    scheduler.start()


def stop_scheduler():
    if scheduler.running: scheduler.shutdown()
