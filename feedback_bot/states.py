from aiogram.fsm.state import State, StatesGroup

class FeedbackStates(StatesGroup):
    waiting_feedback_text = State()
    waiting_rating = State()
    waiting_phone = State()
