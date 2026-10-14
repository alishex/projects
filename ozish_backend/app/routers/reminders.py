from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Reminder, User
from app.schemas import ReminderIn, ReminderOut

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
def list_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Reminder).filter(Reminder.user_id == current_user.id).all()


@router.post("", response_model=ReminderOut)
def create_reminder(
    payload: ReminderIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reminder = Reminder(user_id=current_user.id, **payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Reminder).filter(Reminder.id == reminder_id, Reminder.user_id == current_user.id).delete()
    db.commit()
