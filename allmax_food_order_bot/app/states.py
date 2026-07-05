from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    waiting_meal1 = State()
    waiting_meal2 = State()
    confirming = State()
