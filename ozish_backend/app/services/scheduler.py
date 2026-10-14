import datetime as dt

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import PushToken, Reminder
from app.services.push_service import send_push

_scheduler = BackgroundScheduler(timezone="Asia/Tashkent")


def _run_due_reminders() -> None:
    now_label = dt.datetime.now().strftime("%H:%M")
    db = SessionLocal()
    try:
        due = (
            db.query(Reminder)
            .filter(Reminder.enabled.is_(True), Reminder.time_of_day == now_label)
            .all()
        )
        for reminder in due:
            tokens = [
                row.expo_push_token
                for row in db.query(PushToken).filter(PushToken.user_id == reminder.user_id).all()
            ]
            send_push(tokens, "Ozish", reminder.label)
    finally:
        db.close()


def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.add_job(_run_due_reminders, "cron", minute="*", id="reminders", replace_existing=True)
        _scheduler.start()
