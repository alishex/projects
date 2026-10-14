from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import PushToken, User
from app.schemas import PushTokenIn

router = APIRouter(prefix="/push", tags=["push"])


@router.post("/register", status_code=204)
def register_push_token(
    payload: PushTokenIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(PushToken).filter(PushToken.expo_push_token == payload.expo_push_token).first()
    if existing:
        existing.user_id = current_user.id
    else:
        db.add(PushToken(user_id=current_user.id, expo_push_token=payload.expo_push_token))
    db.commit()
