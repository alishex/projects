"""Finite state machine definitions for user workflows."""
from aiogram.fsm.state import State, StatesGroup


class CreateTaskStates(StatesGroup):
    waiting_title = State()
    waiting_short_title = State()
    waiting_priority = State()
    waiting_confirmation = State()


class DeadlineProposalStates(StatesGroup):
    waiting_deadline = State()


class DeadlineEditStates(StatesGroup):
    waiting_deadline = State()


class SettingsStates(StatesGroup):
    waiting_user_id = State()


class ManageTaskStates(StatesGroup):
    waiting_deadline = State()
    waiting_title = State()
    waiting_short_title = State()
    waiting_priority = State()
    waiting_employee = State()
