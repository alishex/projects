from aiogram.fsm.state import State, StatesGroup


class ResumeFlow(StatesGroup):
    filling = State()
    work_count = State()
    work_detail = State()
    photo = State()
    consent = State()
    interview = State()


class AdminFlow(StatesGroup):
    interview_info = State()
    note = State()


class DynamicAdminFlow(StatesGroup):
    vacancy_name_uz = State()
    vacancy_name_ru = State()
    vacancy_description = State()
    vacancy_responsibilities = State()
    vacancy_requirements = State()
    vacancy_schedule_custom = State()
    vacancy_edit_value = State()
    regulation_title = State()
    regulation_upload_file = State()
    regulation_update_file = State()
    material_edit_value = State()
    question_edit_value = State()


class FollowupFlow(StatesGroup):
    waiting_reply = State()
