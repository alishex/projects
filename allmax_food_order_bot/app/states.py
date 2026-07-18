from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    waiting_meal1 = State()
    waiting_meal2 = State()
    confirming = State()


class ReportStates(StatesGroup):
    waiting_video = State()


class FeedbackStates(StatesGroup):
    waiting_text = State()
