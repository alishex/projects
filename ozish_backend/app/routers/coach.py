from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CoachMessage, FoodLog, User, WeightLog
from app.schemas import CoachChatIn, CoachChatOut
from app.services.claude_client import CoachUnavailable, coach_reply

router = APIRouter(prefix="/coach", tags=["coach"])


def _build_context(db: Session, user: User) -> str:
    recent_food = (
        db.query(FoodLog)
        .filter(FoodLog.user_id == user.id)
        .order_by(FoodLog.logged_at.desc())
        .limit(10)
        .all()
    )
    recent_weight = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user.id)
        .order_by(WeightLog.logged_at.desc())
        .limit(5)
        .all()
    )
    lines = []
    if user.target_weight_kg:
        lines.append(f"Maqsad vazn: {user.target_weight_kg} kg")
    if recent_weight:
        lines.append("So'nggi vazn yozuvlari: " + ", ".join(f"{w.weight_kg}kg" for w in recent_weight))
    if recent_food:
        lines.append(
            "Bugungi/so'nggi taomlar: "
            + ", ".join(f"{f.description} (~{f.calories or '?'} kcal)" for f in recent_food)
        )
    return "\n".join(lines) or "Hali ma'lumot kiritilmagan."


@router.post("", response_model=CoachChatOut)
def chat(
    payload: CoachChatIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.add(CoachMessage(user_id=current_user.id, role="user", content=payload.message))
    db.commit()

    history_rows = (
        db.query(CoachMessage)
        .filter(CoachMessage.user_id == current_user.id)
        .order_by(CoachMessage.created_at.desc())
        .limit(20)
        .all()
    )
    history = [{"role": row.role, "content": row.content} for row in reversed(history_rows)]

    try:
        reply = coach_reply(history, _build_context(db, current_user))
    except CoachUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "AI murabbiy hozircha mavjud emas. Birozdan so'ng qayta urinib ko'ring.",
        )

    db.add(CoachMessage(user_id=current_user.id, role="assistant", content=reply))
    db.commit()
    return CoachChatOut(reply=reply)
