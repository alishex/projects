from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    waiting_meal1 = State()
    waiting_meal2 = State()
    confirming = State()


class ReportStates(StatesGroup):
    waiting_video = State()


class FeedbackStates(StatesGroup):
    waiting_text = State()


class OwnerEdit(StatesGroup):
    """Owner panelning matn-kutuvchi bosqichlari (tugma bosilgach, keyingi
    xabar shu state orqali ushlanadi)."""
    waiting_dept_admin_id = State()
    waiting_dept_deputy_id = State()
    waiting_owner_id = State()
    waiting_schedule_time = State()
    waiting_menu_day_text = State()
    waiting_new_dept_name = State()
    waiting_new_dept_emoji = State()
    waiting_fixed_value = State()
    waiting_override_meal1 = State()
    waiting_override_meal2 = State()
