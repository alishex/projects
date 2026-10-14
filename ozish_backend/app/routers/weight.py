import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, WeightLog
from app.schemas import WeightLogCreate, WeightLogOut

router = APIRouter(prefix="/weight-logs", tags=["weight"])


@router.post("", response_model=WeightLogOut)
def create_weight_log(
    payload: WeightLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = WeightLog(
        user_id=current_user.id,
        weight_kg=payload.weight_kg,
        logged_at=payload.logged_at or dt.datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[WeightLogOut])
def list_weight_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(WeightLog)
        .filter(WeightLog.user_id == current_user.id)
        .order_by(WeightLog.logged_at.asc())
        .all()
    )
