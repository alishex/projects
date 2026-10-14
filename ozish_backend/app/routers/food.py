import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import FoodLog, User
from app.schemas import FoodLogCreate, FoodLogOut
from app.services.claude_client import estimate_nutrition

router = APIRouter(prefix="/food-logs", tags=["food"])


@router.post("", response_model=FoodLogOut)
def create_food_log(
    payload: FoodLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    nutrition = estimate_nutrition(payload.description)
    log = FoodLog(
        user_id=current_user.id,
        description=payload.description,
        meal_type=payload.meal_type,
        logged_at=payload.logged_at or dt.datetime.utcnow(),
        calories=nutrition.get("calories"),
        protein_g=nutrition.get("protein_g"),
        carbs_g=nutrition.get("carbs_g"),
        fat_g=nutrition.get("fat_g"),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[FoodLogOut])
def list_food_logs(
    date: Optional[dt.date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(FoodLog).filter(FoodLog.user_id == current_user.id)
    if date:
        start = dt.datetime.combine(date, dt.time.min)
        end = dt.datetime.combine(date, dt.time.max)
        q = q.filter(FoodLog.logged_at.between(start, end))
    return q.order_by(FoodLog.logged_at.desc()).all()


@router.delete("/{log_id}", status_code=204)
def delete_food_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(FoodLog).filter(FoodLog.id == log_id, FoodLog.user_id == current_user.id).delete()
    db.commit()
