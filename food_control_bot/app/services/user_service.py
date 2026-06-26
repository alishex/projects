from typing import Optional
import app.database as db
import app.config as cfg


async def is_admin(telegram_id: int) -> bool:
    if telegram_id == cfg.SUPER_ADMIN_ID:
        return True
    user = await db.get_user(telegram_id)
    return user is not None and user["role"] == "admin"


async def is_registered(telegram_id: int) -> bool:
    user = await db.get_user(telegram_id)
    return user is not None and user["is_active"] == 1


async def get_display_name(user: dict) -> str:
    if user.get("username"):
        return f"@{user['username']}"
    return user.get("full_name") or f"User_{user['telegram_id']}"


async def get_all_participants() -> list[dict]:
    return await db.get_all_active_users()


async def get_started_users() -> list[dict]:
    users = await db.get_all_active_users()
    return [u for u in users if u["has_started"] == 1]


async def get_not_started_users() -> list[dict]:
    users = await db.get_all_active_users()
    return [u for u in users if u["has_started"] == 0]
