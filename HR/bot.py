import asyncio
import json
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ================== SOZLAMALAR ==================
BOT_TOKEN = "8320901070:AAGzVfu2O4tj2R79mIgeBfxqV1zxz-W8i3A"   # o'zingni token
HR_CHAT_ID = 8148326552  # HR gruppa / lichka ID
START_IMAGE_PATH = "allmax_hr_start.jpg"  # /start uchun rasm

CONFIG_PATH = "config.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CFG = json.load(f)

# Unicode shrift
pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))

# jami savol soni (autobio... achievements + department + role + shift)
TOTAL_QUESTIONS = 18

# State-lar
(
    LANG,
    Q_AUTOBIO,
    Q_ADDRESS,
    Q_PHONE,
    Q_EDU,
    Q_LANGS,
    Q_COMPUTER,
    Q_LASTJOB,
    Q_WHYJOB,
    Q_SOURCE,
    Q_JOBGOAL,
    Q_CHARACTER,
    Q_HIGHGOALS,
    Q_STRENGTHS,
    Q_BOOKS,
    Q_ACHIEVEMENTS,
    Q_DEPARTMENT,
    Q_ROLE,
    Q_SHIFT,
    CONFIRM,
    EDIT_FIELD,
    DONE,          # ✅ yakuniy state
) = range(22)

# ====== DEPARTMENT -> SHIFT xaritasi (kod ichida) ======

DEPARTMENT_SHIFTS = {
    "uz": {
        "Savdo": ["9:00 - 17:00", "15:00 - 23:00", "23:00 - 9:00"],
        "Marketing": ["9:00 - 19:00"],
        "WMS": ["9:00 - 17:00", "15:00 - 23:00"],
        "Moliya": ["9:00 - 17:00", "15:00 - 23:00", "23:00 - 9:00"],
    },
    "ru": {
        "Продажи": ["9:00 - 17:00", "15:00 - 23:00", "23:00 - 9:00"],
        "Маркетинг": ["9:00 - 19:00"],
        "WMS": ["9:00 - 17:00", "15:00 - 23:00"],
        "Финансы": ["9:00 - 17:00", "15:00 - 23:00", "23:00 - 9:00"],
    },
    "en": {
        "Sales": ["9:00 - 17:00", "15:00 - 23:00", "23:00 - 9:00"],
        "Marketing": ["9:00 - 19:00"],
        "WMS": ["9:00 - 17:00", "15:00 - 23:00"],
        "Finance": ["9:00 - 17:00", "15:00 - 23:00", "23:00 - 9:00"],
    },
}

# DEPARTMENT -> ROLE xaritasi (kod ichida)

DEPARTMENT_ROLES = {
    "uz": {
        "Savdo": ["Consultant", "Merchandiser"],
        "Marketing": [
            "Mobilograf",
            "Dizayner",
            "Community Manager",
            "SMM Manager",
            "Brand Face",
        ],
        "WMS": ["Qabul", "Jo'natish"],
        "Moliya": ["Kassir"],
    },
    "ru": {
        "Продажи": ["Консультант", "Мерчендайзер"],
        "Маркетинг": [
            "Мобилограф",
            "Дизайнер",
            "Community Manager",
            "SMM Manager",
            "Brand Face",
        ],
        "WMS": ["Приём товара", "Отгрузка"],
        "Финансы": ["Кассир"],
    },
    "en": {
        "Sales": ["Consultant", "Merchandiser"],
        "Marketing": [
            "Mobileographer",
            "Designer",
            "Community Manager",
            "SMM Manager",
            "Brand Face",
        ],
        "WMS": ["Receiving", "Shipping"],
        "Finance": ["Cashier"],
    },
}

# default shiftlar (agar mapping topilmasa)
DEFAULT_SHIFTS = ["9:00 - 17:00", "15:00 - 23:00"]

BACK_BTN = {
    "uz": "⬅️ Orqaga",
    "ru": "⬅️ Назад",
    "en": "⬅️ Back",
}

BACK_DEPT_BTN = {
    "uz": "⬅️ Bo‘limni o‘zgartirish",
    "ru": "⬅️ Изменить отдел",
    "en": "⬅️ Change department",
}

BACK_ROLE_BTN = {
    "uz": "⬅️ Orqaga (rolni o‘zgartirish)",
    "ru": "⬅️ Назад (изменить роль)",
    "en": "⬅️ Back (change role)",
}

# ✅ yakunda ko‘rinadigan "Qayta to‘ldirish" tugmasi
RESTART_BTN = {
    "uz": "🔁 Qayta to‘ldirish",
    "ru": "🔁 Заполнить заново",
    "en": "🔁 Fill again",
}

# Tahrirlash uchun maydonlar (confirm ekrandan tanlash)
EDITABLE_FIELDS = [
    ("autobio", "autobio"),
    ("address", "address"),
    ("phone", "phone"),
    ("education", "education"),
    ("foreign_langs", "foreign_langs"),
    ("computer_skills", "computer_skills"),
    ("last_job", "last_job"),
    ("why_this_job", "why_this_job"),
    ("source", "source"),
    ("job_goal", "job_goal"),
    ("character", "character"),
    ("high_goals", "high_goals"),
    ("strengths_weaknesses", "strengths_weaknesses"),
    ("books", "books"),
    ("achievements", "achievements"),
    ("department_block", None),  # bo‘lim + rol + smena
]


# =============== YORDAMCHI FUNKSIYALAR =================

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "uz")


def base_prompt(key: str, lang: str) -> str:
    return CFG["questions"][key]["prompt"][lang]


def label_text(key: str, lang: str) -> str:
    return CFG["questions"][key]["label"][lang]


def make_prompt(key: str, lang: str, index: int) -> str:
    """Savol uchun progress bilan matn: (3/18) ... Qolgan: ..."""
    remaining = TOTAL_QUESTIONS - index
    if lang == "uz":
        prefix = f"({index}/{TOTAL_QUESTIONS}) Savol. Qolgan savollar: {remaining} ta.\n\n"
    elif lang == "ru":
        prefix = f"({index}/{TOTAL_QUESTIONS}) Вопрос. Осталось: {remaining}.\n\n"
    else:
        prefix = f"({index}/{TOTAL_QUESTIONS}) Question. Remaining: {remaining}.\n\n"
    return prefix + base_prompt(key, lang)


def is_phone_valid(p: str) -> bool:
    return any(ch.isdigit() for ch in p)


# ---------- PDF GENERATOR (DejaVu shrift bilan) ----------

def wrap_text(text: str, max_width: float, canv: canvas.Canvas, font="DejaVu", size=9):
    text = (text or "").replace("\r", " ").strip()
    if not text:
        return [""]
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if canv.stringWidth(test, font, size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def generate_pdf(data: dict, lang: str, username: str = None, phone: str = None) -> BytesIO:
    """Javoblar bo'yicha PDF anketa yaratadi va BytesIO qaytaradi."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    left = 18 * mm
    right = width - 18 * mm
    y = height - 22 * mm

    # Sarlavha
    c.setFont("DejaVu", 18)
    c.drawCentredString(width / 2, y, CFG["meta"]["title"][lang])
    y -= 6 * mm
    c.setFont("DejaVu", 10)
    c.drawCentredString(width / 2, y, CFG["meta"]["address"][lang])
    y -= 8 * mm

    # Yuqoriga chiziq
    c.line(left, y, right, y)
    y -= 6 * mm

    c.setFont("DejaVu", 9)

    def new_page_header():
        nonlocal y
        c.showPage()
        y = height - 22 * mm
        c.setFont("DejaVu", 14)
        c.drawCentredString(width / 2, y, CFG["meta"]["title"][lang])
        y -= 4 * mm
        c.setFont("DejaVu", 9)
        c.line(left, y, right, y)
        y -= 6 * mm

    def draw_field(label_key: str, answer_key: str, custom_label: str = None):
        """JSON label yoki custom_label bilan maydon chizish."""
        nonlocal y
        label = custom_label if custom_label is not None else label_text(label_key, lang)
        answer = data.get(answer_key, "")

        if y < 18 * mm:
            new_page_header()

        # label
        c.setFont("DejaVu", 9)
        c.drawString(left, y, label)
        y -= 3 * mm

        # chiziq
        line_y = y
        c.line(left, line_y, right, line_y)
        y -= 3 * mm

        # answer
        c.setFont("DejaVu", 8.5)
        max_w = right - left
        lines = wrap_text(answer, max_w, c, "DejaVu", 8.5)
        for line in lines:
            if line:
                c.drawString(left + 1.5 * mm, y, line)
                y -= 3.4 * mm
        y -= 2 * mm

    # JSONdagi maydonlar
    order = [
        ("autobio", "autobio"),
        ("address", "address"),
        ("phone", "phone"),
        ("education", "education"),
        ("foreign_langs", "foreign_langs"),
        ("computer_skills", "computer_skills"),
        ("last_job", "last_job"),
        ("why_this_job", "why_this_job"),
        ("source", "source"),
        ("job_goal", "job_goal"),
        ("character", "character"),
        ("high_goals", "high_goals"),
        ("strengths_weaknesses", "strengths_weaknesses"),
        ("books", "books"),
        ("achievements", "achievements"),
        ("department", "department"),
        # role + shift custom label bilan chiziladi
    ]

    for l_key, a_key in order:
        draw_field(l_key, a_key)

    if y < 22 * mm:
        new_page_header()

    # role label
    if lang == "uz":
        role_label = "Tanlangan rol"
    elif lang == "ru":
        role_label = "Выбранная роль"
    else:
        role_label = "Selected role"

    draw_field("role", "role", custom_label=role_label)

    if y < 22 * mm:
        new_page_header()

    # shift label
    if lang == "uz":
        shift_label = "Ish smenasi"
    elif lang == "ru":
        shift_label = "Рабочая смена"
    else:
        shift_label = "Work shift"

    draw_field("shift", "shift", custom_label=shift_label)

    # Sana + kandidat ma'lumoti + izoh
    if y < 22 * mm:
        new_page_header()

    today_label = CFG["meta"]["today_label"][lang]
    today_str = datetime.now().strftime("%Y-%m-%d")

    # username / phone formatlash
    uname = (username or "").strip()
    if uname and not uname.startswith("@"):
        uname = "@" + uname
    if not uname:
        uname = "—"

    phone_disp = phone or "—"

    if lang == "uz":
        cand_label = "Nomzod"
    elif lang == "ru":
        cand_label = "Кандидат"
    else:
        cand_label = "Candidate"

    candidate_line = f"{cand_label}: {uname} | Tel: {phone_disp}"

    # Kandidat ma'lumoti
    c.setFont("DejaVu", 8.5)
    c.drawString(left, 20 * mm, candidate_line)

    # Sana
    c.setFont("DejaVu", 9)
    c.drawString(left, 16 * mm, f"{today_label}: {today_str}")

    # Footer izoh
    c.setFont("DejaVu", 7.5)
    footer = CFG["meta"]["footer_note"][lang]
    max_w = right - left
    f_lines = wrap_text(footer, max_w, c, "DejaVu", 7.5)
    fy = 11 * mm
    for line in f_lines:
        c.drawString(left, fy, line)
        fy -= 3 * mm

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def build_summary_text(lang: str, data: dict) -> str:
    """Xulosa postini matn ko'rinishida qaytaradi."""
    if lang == "uz":
        header = "🧾 ALLMAX ANKETA XULOSASI\n────────────────────────\n"
        block1 = "👤 Shaxsiy ma'lumotlar:\n"
        block2 = "🎓 Ta'lim va ko‘nikmalar:\n"
        block3 = "💼 Ish va maqsadlar:\n"
        block4 = "🧠 Xarakter va shaxsiy rivojlanish:\n"
        block5 = "🏢 Bo‘lim va ish smenasi:\n"
        footer_text = CFG["confirm"]["message"]["uz"]
        dept_label = label_text("department", lang)
        role_label = "Tanlangan rol"
        shift_label = "Ish smenasi"
    elif lang == "ru":
        header = "🧾 РЕЗЮМЕ АНКЕТЫ ALLMAX\n────────────────────────\n"
        block1 = "👤 Личные данные:\n"
        block2 = "🎓 Образование и навыки:\n"
        block3 = "💼 Работа и цели:\n"
        block4 = "🧠 Характер и личностное развитие:\n"
        block5 = "🏢 Отдел и график работы:\n"
        footer_text = CFG["confirm"]["message"]["ru"]
        dept_label = label_text("department", lang)
        role_label = "Выбранная роль"
        shift_label = "Рабочая смена"
    else:
        header = "🧾 ALLMAX APPLICATION SUMMARY\n────────────────────────\n"
        block1 = "👤 Personal information:\n"
        block2 = "🎓 Education & skills:\n"
        block3 = "💼 Job & goals:\n"
        block4 = "🧠 Character & personal growth:\n"
        block5 = "🏢 Department & work shift:\n"
        footer_text = CFG["confirm"]["message"]["en"]
        dept_label = label_text("department", lang)
        role_label = "Selected role"
        shift_label = "Work shift"

    lines_block1 = [
        f"• {label_text('autobio', lang)}: {data.get('autobio','')}",
        f"• {label_text('address', lang)}: {data.get('address','')}",
        f"• {label_text('phone', lang)}: {data.get('phone','')}",
    ]

    lines_block2 = [
        f"• {label_text('education', lang)}: {data.get('education','')}",
        f"• {label_text('foreign_langs', lang)}: {data.get('foreign_langs','')}",
        f"• {label_text('computer_skills', lang)}: {data.get('computer_skills','')}",
    ]

    lines_block3 = [
        f"• {label_text('last_job', lang)}: {data.get('last_job','')}",
        f"• {label_text('why_this_job', lang)}: {data.get('why_this_job','')}",
        f"• {label_text('source', lang)}: {data.get('source','')}",
        f"• {label_text('job_goal', lang)}: {data.get('job_goal','')}",
    ]

    lines_block4 = [
        f"• {label_text('character', lang)}: {data.get('character','')}",
        f"• {label_text('high_goals', lang)}: {data.get('high_goals','')}",
        f"• {label_text('strengths_weaknesses', lang)}: {data.get('strengths_weaknesses','')}",
        f"• {label_text('books', lang)}: {data.get('books','')}",
        f"• {label_text('achievements', lang)}: {data.get('achievements','')}",
    ]

    lines_block5 = [
        f"• {dept_label}: {data.get('department','')}",
        f"• {role_label}: {data.get('role','')}",
        f"• {shift_label}: {data.get('shift','')}",
    ]

    summary = (
        header
        + block1
        + "\n".join(lines_block1)
        + "\n\n"
        + block2
        + "\n".join(lines_block2)
        + "\n\n"
        + block3
        + "\n".join(lines_block3)
        + "\n\n"
        + block4
        + "\n".join(lines_block4)
        + "\n\n"
        + block5
        + "\n".join(lines_block5)
        + "\n\n"
        + footer_text
    )
    return summary


async def send_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xulosa postini chiqarish + tasdiqlash / tahrirlash tugmalari."""
    lang = get_lang(context)
    data = context.user_data

    summary = build_summary_text(lang, data)

    yes_btn = CFG["confirm"]["buttons"]["yes"][lang]
    no_btn = CFG["confirm"]["buttons"]["no"][lang]
    edit_btn = CFG["confirm"]["buttons"]["edit"][lang]

    keyboard = [[yes_btn], [edit_btn], [no_btn]]

    await update.message.reply_text(
        summary,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


# =============== HANDLERLAR =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start bosilganda Allmax HR rasmi + salomlashish matni + til tanlash knopkalari.
    """
    chat_id = update.effective_chat.id

    # Til tanlash knopkalari
    buttons = [
        [CFG["start"]["languages_buttons"]["uz"]],
        [CFG["start"]["languages_buttons"]["ru"]],
        [CFG["start"]["languages_buttons"]["en"]],
    ]
    reply_kb = ReplyKeyboardMarkup(
        buttons, resize_keyboard=True, one_time_keyboard=True
    )

    # Rasm ostidagi yozuv (RU + UZ + EN)
    caption = (
        "Приветствую Вас, я HR-бот ALLMAX Fix Price 👋\n\n"
        "🤖 Я:\n"
        "- расскажу Вам о компании и о преимуществах работы у нас;\n"
        "- помогу найти актуальные вакансии и заполнить анкету.\n\n"
        "Работа в ALLMAX становится всё лучше и лучше.\n"
        "____________________________\n\n"
        "Xush kelibsiz, men HR-bot ALLMAX Fix Price 👋\n\n"
        "🤖 Men:\n"
        "- sizga kompaniya haqida va biz bilan ishlashning afzalliklari haqida gapirib beraman;\n"
        "- mavjud vakansiyalarni topishga va so'rovnomani to'ldirishga yordam beraman.\n\n"
        "ALLMAXda ish – odatdagidan yaxshiroq.\n"
        "____________________________\n\n"
        "Welcome, I'm the HR-bot of ALLMAX Fix Price 👋\n\n"
        "🤖 I will:\n"
        "- tell you about our company and the benefits of working with us;\n"
        "- help you find suitable vacancies and fill out the application form.\n\n"
        "Work at ALLMAX is better than usual.\n\n"
        "Tilni tanlang / Выберите язык / Choose a language 👇"
    )

    # Rasm + caption + knopkalar
    with open(START_IMAGE_PATH, "rb") as photo:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=caption,
            reply_markup=reply_kb,
        )

    return LANG


async def choose_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == CFG["start"]["languages_buttons"]["uz"]:
        lang = "uz"
    elif text == CFG["start"]["languages_buttons"]["ru"]:
        lang = "ru"
    elif text == CFG["start"]["languages_buttons"]["en"]:
        lang = "en"
    else:
        lang = "uz"

    context.user_data["lang"] = lang

    await update.message.reply_text(
        make_prompt("autobio", lang, 1),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_AUTOBIO


async def q_autobio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    # orqaga – til tanlashga qaytish
    if text == BACK_BTN[lang]:
        buttons = [
            [CFG["start"]["languages_buttons"]["uz"]],
            [CFG["start"]["languages_buttons"]["ru"]],
            [CFG["start"]["languages_buttons"]["en"]],
        ]
        reply_kb = ReplyKeyboardMarkup(
            buttons, resize_keyboard=True, one_time_keyboard=True
        )
        await update.message.reply_text(
            CFG["start"]["choose_language"][lang],
            reply_markup=reply_kb,
        )
        return LANG

    context.user_data["autobio"] = text

    # editing rejimi bo'lsa – faqat shu maydonni almashtirib, xulosa
    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "autobio":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("address", lang, 2),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_ADDRESS


async def q_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        # Avtobiografiyaga qaytish
        await update.message.reply_text(
            make_prompt("autobio", lang, 1),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_AUTOBIO

    context.user_data["address"] = text

    # edit rejimi
    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "address":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    if lang == "uz":
        btn_text = "📱 Raqamni ulashish"
    elif lang == "ru":
        btn_text = "📱 Поделиться номером"
    else:
        btn_text = "📱 Share phone number"

    keyboard = [
        [KeyboardButton(btn_text, request_contact=True)],
        [BACK_BTN[lang]],
    ]
    await update.message.reply_text(
        make_prompt("phone", lang, 3),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
    )
    return Q_PHONE


async def q_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)

    if (
        update.message.text
        and update.message.text.strip() == BACK_BTN[lang]
        and not update.message.contact
        and not context.user_data.get("edit_mode")
    ):
        # manzil savoliga qaytish
        await update.message.reply_text(
            make_prompt("address", lang, 2),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_ADDRESS

    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    if not is_phone_valid(phone):
        if lang == "uz":
            msg = "Telefon raqam noto‘g‘ri. Iltimos, qayta kiriting:"
        elif lang == "ru":
            msg = "Неверный номер телефона. Пожалуйста, введите снова:"
        else:
            msg = "Phone number seems invalid. Please enter again:"
        await update.message.reply_text(msg)
        return Q_PHONE

    context.user_data["phone"] = phone

    # edit rejimi
    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "phone":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    edu_opts = CFG["questions"]["education"]["options"][lang]
    keyboard = [
        [edu_opts[0], edu_opts[1]],
        [edu_opts[2]],
        [BACK_BTN[lang]],
    ]
    await update.message.reply_text(
        make_prompt("education", lang, 4),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return Q_EDU


async def q_edu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()
    edu_opts = CFG["questions"]["education"]["options"][lang]

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        # phone savoliga qaytish
        if lang == "uz":
            btn_text = "📱 Raqamni ulashish"
        elif lang == "ru":
            btn_text = "📱 Поделиться номером"
        else:
            btn_text = "📱 Share phone number"

        keyboard = [
            [KeyboardButton(btn_text, request_contact=True)],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("phone", lang, 3),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        )
        return Q_PHONE

    if text not in edu_opts:
        keyboard = [
            [edu_opts[0], edu_opts[1]],
            [edu_opts[2]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("education", lang, 4),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_EDU

    context.user_data["education"] = text

    # edit rejimi
    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "education":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("foreign_langs", lang, 5),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_LANGS


async def q_langs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        # education savoliga qaytish
        edu_opts = CFG["questions"]["education"]["options"][lang]
        keyboard = [
            [edu_opts[0], edu_opts[1]],
            [edu_opts[2]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("education", lang, 4),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_EDU

    context.user_data["foreign_langs"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "foreign_langs":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("computer_skills", lang, 6),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_COMPUTER


async def q_computer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("foreign_langs", lang, 5),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_LANGS

    context.user_data["computer_skills"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "computer_skills":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("last_job", lang, 7),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_LASTJOB


async def q_lastjob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("computer_skills", lang, 6),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_COMPUTER

    context.user_data["last_job"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "last_job":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("why_this_job", lang, 8),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_WHYJOB


async def q_whyjob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("last_job", lang, 7),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_LASTJOB

    context.user_data["why_this_job"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "why_this_job":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    src_opts = CFG["questions"]["source"]["options"][lang]
    keyboard = [
        [src_opts[0], src_opts[1]],
        [src_opts[2], src_opts[3]],
        [src_opts[4], src_opts[5]],
        [BACK_BTN[lang]],
    ]
    await update.message.reply_text(
        make_prompt("source", lang, 9),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return Q_SOURCE


async def q_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()
    src_opts = CFG["questions"]["source"]["options"][lang]
    other = src_opts[-1]

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode") and not context.user_data.get("source_custom_wait"):
        await update.message.reply_text(
            make_prompt("why_this_job", lang, 8),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_WHYJOB

    # "Boshqa"/"Other" bosilganda
    if text == other and not context.user_data.get("source_custom_wait"):
        if lang == "uz":
            msg = "Iltimos, ish haqida qayerdan bilganingizni yozing:"
        elif lang == "ru":
            msg = "Пожалуйста, напишите, откуда узнали о вакансии:"
        else:
            msg = "Please type how you learned about this vacancy:"
        context.user_data["source_custom_wait"] = True
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
        return Q_SOURCE

    # Boshqa varianti matn shaklida
    if context.user_data.get("source_custom_wait"):
        context.user_data["source"] = text
        context.user_data.pop("source_custom_wait")

        if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "source":
            context.user_data["edit_mode"] = False
            context.user_data.pop("edit_field", None)
            await send_summary(update, context)
            return CONFIRM

        await update.message.reply_text(
            make_prompt("job_goal", lang, 10),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_JOBGOAL

    # oddiy variantlardan biri
    if text not in src_opts:
        keyboard = [
            [src_opts[0], src_opts[1]],
            [src_opts[2], src_opts[3]],
            [src_opts[4], src_opts[5]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("source", lang, 9),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_SOURCE

    context.user_data["source"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "source":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("job_goal", lang, 10),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_JOBGOAL


async def q_jobgoal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        src_opts = CFG["questions"]["source"]["options"][lang]
        keyboard = [
            [src_opts[0], src_opts[1]],
            [src_opts[2], src_opts[3]],
            [src_opts[4], src_opts[5]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("source", lang, 9),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_SOURCE

    context.user_data["job_goal"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "job_goal":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("character", lang, 11),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_CHARACTER


async def q_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("job_goal", lang, 10),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_JOBGOAL

    context.user_data["character"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "character":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("high_goals", lang, 12),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_HIGHGOALS


async def q_highgoals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("character", lang, 11),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_CHARACTER

    context.user_data["high_goals"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "high_goals":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("strengths_weaknesses", lang, 13),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_STRENGTHS


async def q_strengths(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("high_goals", lang, 12),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_HIGHGOALS

    context.user_data["strengths_weaknesses"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "strengths_weaknesses":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("books", lang, 14),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_BOOKS


async def q_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("strengths_weaknesses", lang, 13),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_STRENGTHS

    context.user_data["books"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "books":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    await update.message.reply_text(
        make_prompt("achievements", lang, 15),
        reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
    )
    return Q_ACHIEVEMENTS


async def q_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()

    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("books", lang, 14),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_BOOKS

    context.user_data["achievements"] = text

    if context.user_data.get("edit_mode") and context.user_data.get("edit_field") == "achievements":
        context.user_data["edit_mode"] = False
        context.user_data.pop("edit_field", None)
        await send_summary(update, context)
        return CONFIRM

    # Department variantlari JSONdan olinadi
    dept_opts = CFG["questions"]["department"]["options"][lang]
    keyboard = [
        [dept_opts[0], dept_opts[1]],
        [dept_opts[2], dept_opts[3]],
        [BACK_BTN[lang]],
    ]
    await update.message.reply_text(
        make_prompt("department", lang, 16),
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return Q_DEPARTMENT


async def q_department(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    department = update.message.text.strip()
    dept_opts = CFG["questions"]["department"]["options"][lang]

    if department == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("achievements", lang, 15),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_ACHIEVEMENTS

    if department not in dept_opts:
        keyboard = [
            [dept_opts[0], dept_opts[1]],
            [dept_opts[2], dept_opts[3]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("department", lang, 16),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_DEPARTMENT

    context.user_data["department"] = department

    # Rol variantlari
    roles = DEPARTMENT_ROLES.get(lang, {}).get(department, [])
    if not roles:
        roles = ["Xodim"]

    # tugmalar: 2 tadan ustun + orqaga
    keyboard_rows = []
    row = []
    for r in roles:
        row.append(r)
        if len(row) == 2:
            keyboard_rows.append(row)
            row = []
    if row:
        keyboard_rows.append(row)

    keyboard_rows.append([BACK_DEPT_BTN[lang]])
    keyboard_rows.append([BACK_BTN[lang]])

    if lang == "uz":
        prompt = f"({17}/{TOTAL_QUESTIONS}) Savol.\n\nTanlagan bo‘limingiz ichida qaysi rolda ishlamoqchisiz?"
    elif lang == "ru":
        prompt = f"({17}/{TOTAL_QUESTIONS}) Вопрос.\n\nВ какой роли вы хотите работать в этом отделе?"
    else:
        prompt = f"({17}/{TOTAL_QUESTIONS}) Question.\n\nWhich role do you want to work in this department?"

    await update.message.reply_text(
        prompt,
        reply_markup=ReplyKeyboardMarkup(keyboard_rows, resize_keyboard=True),
    )
    return Q_ROLE


async def q_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()
    department = context.user_data.get("department")

    # Bo'limni o‘zgartirish
    if text == BACK_DEPT_BTN[lang]:
        dept_opts = CFG["questions"]["department"]["options"][lang]
        keyboard = [
            [dept_opts[0], dept_opts[1]],
            [dept_opts[2], dept_opts[3]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("department", lang, 16),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_DEPARTMENT

    # umumiy orqaga – achievementsga
    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("achievements", lang, 15),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_ACHIEVEMENTS

    roles = DEPARTMENT_ROLES.get(lang, {}).get(department, [])
    if not roles:
        roles = ["Xodim"]

    if text not in roles:
        keyboard_rows = []
        row = []
        for r in roles:
            row.append(r)
            if len(row) == 2:
                keyboard_rows.append(row)
                row = []
        if row:
            keyboard_rows.append(row)
        keyboard_rows.append([BACK_DEPT_BTN[lang]])
        keyboard_rows.append([BACK_BTN[lang]])

        if lang == "uz":
            prompt = f"({17}/{TOTAL_QUESTIONS}) Savol.\n\nIltimos, roldan birini tanlang:"
        elif lang == "ru":
            prompt = f"({17}/{TOTAL_QUESTIONS}) Вопрос.\n\nПожалуйста, выберите одну из ролей:"
        else:
            prompt = f"({17}/{TOTAL_QUESTIONS}) Question.\n\nPlease select one of the roles:"

        await update.message.reply_text(
            prompt,
            reply_markup=ReplyKeyboardMarkup(keyboard_rows, resize_keyboard=True),
        )
        return Q_ROLE

    # valid rol
    context.user_data["role"] = text

    # Shiftlar (bo‘lim bo‘yicha)
    shifts = DEPARTMENT_SHIFTS.get(lang, {}).get(department)
    if not shifts:
        shifts = DEFAULT_SHIFTS

    keyboard = [[s] for s in shifts]
    keyboard.append([BACK_ROLE_BTN[lang]])
    keyboard.append([BACK_BTN[lang]])

    if lang == "uz":
        prompt = f"({18}/{TOTAL_QUESTIONS}) Savol.\n\nQaysi ish smenasi sizga qulay? ⏰"
    elif lang == "ru":
        prompt = f"({18}/{TOTAL_QUESTIONS}) Вопрос.\n\nКакой график работы вам удобнее? ⏰"
    else:
        prompt = f"({18}/{TOTAL_QUESTIONS}) Question.\n\nWhich work shift suits you best? ⏰"

    await update.message.reply_text(
        prompt,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return Q_SHIFT


async def q_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()
    department = context.user_data.get("department")

    # Orqaga (rolga qaytish)
    if text == BACK_ROLE_BTN[lang]:
        roles = DEPARTMENT_ROLES.get(lang, {}).get(department, [])
        if not roles:
            roles = ["Xodim"]

        keyboard_rows = []
        row = []
        for r in roles:
            row.append(r)
            if len(row) == 2:
                keyboard_rows.append(row)
                row = []
        if row:
            keyboard_rows.append(row)
        keyboard_rows.append([BACK_DEPT_BTN[lang]])
        keyboard_rows.append([BACK_BTN[lang]])

        if lang == "uz":
            prompt = f"({17}/{TOTAL_QUESTIONS}) Savol.\n\nTanlagan bo‘limingiz ichida qaysi rolda ishlamoqchisiz?"
        elif lang == "ru":
            prompt = f"({17}/{TOTAL_QUESTIONS}) Вопрос.\n\nВ какой роли вы хотите работать в этом отделе?"
        else:
            prompt = f"({17}/{TOTAL_QUESTIONS}) Question.\n\nWhich role do you want to work in this department?"

        await update.message.reply_text(
            prompt,
            reply_markup=ReplyKeyboardMarkup(keyboard_rows, resize_keyboard=True),
        )
        return Q_ROLE

    # umumiy orqaga – achievementsga qaytish mumkin
    if text == BACK_BTN[lang] and not context.user_data.get("edit_mode"):
        await update.message.reply_text(
            make_prompt("achievements", lang, 15),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_ACHIEVEMENTS

    shifts = DEPARTMENT_SHIFTS.get(lang, {}).get(department)
    if not shifts:
        shifts = DEFAULT_SHIFTS

    if text not in shifts:
        keyboard = [[s] for s in shifts]
        keyboard.append([BACK_ROLE_BTN[lang]])
        keyboard.append([BACK_BTN[lang]])

        if lang == "uz":
            prompt = f"({18}/{TOTAL_QUESTIONS}) Savol.\n\nIltimos, smenadan birini tanlang:"
        elif lang == "ru":
            prompt = f"({18}/{TOTAL_QUESTIONS}) Вопрос.\n\nПожалуйста, выберите один из графиков:"
        else:
            prompt = f"({18}/{TOTAL_QUESTIONS}) Question.\n\nPlease select one of the shifts:"

        await update.message.reply_text(
            prompt,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_SHIFT

    # to‘g‘ri shift
    context.user_data["shift"] = text

    # Shift – doim xulosa bilan tugaydi
    await send_summary(update, context)
    return CONFIRM


async def edit_field_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahrirlash uchun bo‘lim tanlash."""
    lang = get_lang(context)
    text = update.message.text.strip()

    # raqam bo'lishi kerak
    try:
        idx = int(text)
    except ValueError:
        if lang == "uz":
            msg = "Iltimos, tahrirlash uchun kerakli bo‘lim raqamini yuboring (masalan, 3)."
        elif lang == "ru":
            msg = "Пожалуйста, отправьте номер раздела для редактирования (например, 3)."
        else:
            msg = "Please send the number of the section you want to edit (e.g. 3)."
        await update.message.reply_text(msg)
        return EDIT_FIELD

    if idx < 1 or idx > len(EDITABLE_FIELDS):
        if lang == "uz":
            msg = "Bunday raqam yo‘q. Qaytadan tanlang."
        elif lang == "ru":
            msg = "Нет такого номера. Пожалуйста, выберите снова."
        else:
            msg = "No such number. Please choose again."
        await update.message.reply_text(msg)
        return EDIT_FIELD

    key, label_key = EDITABLE_FIELDS[idx - 1]

    # Bo‘lim / rol / smena bloki
    if key == "department_block":
        # oddiy department jarayonidan boshlaymiz
        dept_opts = CFG["questions"]["department"]["options"][lang]
        keyboard = [
            [dept_opts[0], dept_opts[1]],
            [dept_opts[2], dept_opts[3]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("department", lang, 16),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        # edit_mode-ni ishlatmaymiz, hammasi qayta tanlanadi
        context.user_data.pop("edit_mode", None)
        context.user_data.pop("edit_field", None)
        return Q_DEPARTMENT

    # boshqa maydonlar uchun – edit_mode yoqiladi
    context.user_data["edit_mode"] = True
    context.user_data["edit_field"] = key

    # qaysi savolga qaytish
    if key == "autobio":
        await update.message.reply_text(
            make_prompt("autobio", lang, 1),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_AUTOBIO
    elif key == "address":
        await update.message.reply_text(
            make_prompt("address", lang, 2),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_ADDRESS
    elif key == "phone":
        if lang == "uz":
            btn_text = "📱 Raqamni ulashish"
        elif lang == "ru":
            btn_text = "📱 Поделиться номером"
        else:
            btn_text = "📱 Share phone number"

        keyboard = [
            [KeyboardButton(btn_text, request_contact=True)],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("phone", lang, 3),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True),
        )
        return Q_PHONE
    elif key == "education":
        edu_opts = CFG["questions"]["education"]["options"][lang]
        keyboard = [
            [edu_opts[0], edu_opts[1]],
            [edu_opts[2]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("education", lang, 4),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_EDU
    elif key == "foreign_langs":
        await update.message.reply_text(
            make_prompt("foreign_langs", lang, 5),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_LANGS
    elif key == "computer_skills":
        await update.message.reply_text(
            make_prompt("computer_skills", lang, 6),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_COMPUTER
    elif key == "last_job":
        await update.message.reply_text(
            make_prompt("last_job", lang, 7),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_LASTJOB
    elif key == "why_this_job":
        await update.message.reply_text(
            make_prompt("why_this_job", lang, 8),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_WHYJOB
    elif key == "source":
        src_opts = CFG["questions"]["source"]["options"][lang]
        keyboard = [
            [src_opts[0], src_opts[1]],
            [src_opts[2], src_opts[3]],
            [src_opts[4], src_opts[5]],
            [BACK_BTN[lang]],
        ]
        await update.message.reply_text(
            make_prompt("source", lang, 9),
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return Q_SOURCE
    elif key == "job_goal":
        await update.message.reply_text(
            make_prompt("job_goal", lang, 10),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_JOBGOAL
    elif key == "character":
        await update.message.reply_text(
            make_prompt("character", lang, 11),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_CHARACTER
    elif key == "high_goals":
        await update.message.reply_text(
            make_prompt("high_goals", lang, 12),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_HIGHGOALS
    elif key == "strengths_weaknesses":
        await update.message.reply_text(
            make_prompt("strengths_weaknesses", lang, 13),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_STRENGTHS
    elif key == "books":
        await update.message.reply_text(
            make_prompt("books", lang, 14),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_BOOKS
    elif key == "achievements":
        await update.message.reply_text(
            make_prompt("achievements", lang, 15),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_ACHIEVEMENTS

    # default holda – xulosaga qaytamiz
    context.user_data["edit_mode"] = False
    context.user_data.pop("edit_field", None)
    await send_summary(update, context)
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text
    yes_btn = CFG["confirm"]["buttons"]["yes"][lang]
    no_btn = CFG["confirm"]["buttons"]["no"][lang]
    edit_btn = CFG["confirm"]["buttons"]["edit"][lang]

    # ✅ tasdiqlash
    if text == yes_btn:
        data = context.user_data

        tg_user = update.effective_user
        username = tg_user.username if tg_user else None
        phone = data.get("phone")

        # username / phone caption uchun format
        uname = (username or "").strip()
        if uname and not uname.startswith("@"):
            uname = "@" + uname
        if not uname:
            uname = "—"
        phone_disp = phone or "—"

        # foydalanuvchi uchun PDF
        pdf_buf = generate_pdf(data, lang, username=username, phone=phone)

        await update.message.reply_document(
            document=pdf_buf,
            filename="allmax_anketa.pdf",
        )

        # HR gruppa uchun PDF
        if HR_CHAT_ID is not None:
            pdf_buf2 = generate_pdf(data, lang, username=username, phone=phone)
            hr_caption = (
                "Yangi ALLMAX anketa\n"
                f"Nomzod: {uname} | Tel: {phone_disp}\n"
            )
            await context.bot.send_document(
                chat_id=HR_CHAT_ID,
                document=pdf_buf2,
                filename="allmax_anketa.pdf",
                caption=hr_caption,
            )

        # ✅ endi DONE state: faqat "Qayta to‘ldirish" va standart xabar
        lang_saved = lang
        context.user_data.clear()
        context.user_data["lang"] = lang_saved

        restart_text = RESTART_BTN[lang]

        final_msg = (
            "Adminlarimiz siz bilan tez orada bog‘lanishadi.\n\n"
            "Agar qandaydir savolingiz bo‘lsa, @ALLMAXHR bilan bog‘lanishingiz mumkin."
        )

        await update.message.reply_text(
            final_msg,
            reply_markup=ReplyKeyboardMarkup(
                [[restart_text]],
                resize_keyboard=True
            ),
        )

        return DONE

    # ✏️ Tahrirlash
    if text == edit_btn:
        # tahrirlash rejimi uchun maydonlar ro'yxati
        lines = []
        for i, (key, label_key) in enumerate(EDITABLE_FIELDS, start=1):
            if key == "department_block":
                if lang == "uz":
                    title = "Bo‘lim / rol / smena"
                elif lang == "ru":
                    title = "Отдел / роль / смена"
                else:
                    title = "Department / role / shift"
            else:
                title = label_text(label_key, lang)
            lines.append(f"{i}. {title}")

        if lang == "uz":
            header = "✏️ Qaysi bo‘limni tahrirlashni xohlaysiz?\n\n"
        elif lang == "ru":
            header = "✏️ Какой раздел вы хотите отредактировать?\n\n"
        else:
            header = "✏️ Which section do you want to edit?\n\n"

        text_msg = header + "\n".join(lines) + "\n\n"

        if lang == "uz":
            text_msg += "Kerakli bo‘lim raqamini yuboring (masalan, 3)."
        elif lang == "ru":
            text_msg += "Отправьте номер нужного раздела (например, 3)."
        else:
            text_msg += "Send the number of the section (e.g. 3)."

        await update.message.reply_text(
            text_msg,
            reply_markup=ReplyKeyboardRemove(),
        )
        return EDIT_FIELD

    # 🔄 boshidan
    if text == no_btn:
        context.user_data.clear()
        await update.message.reply_text(
            make_prompt("autobio", lang, 1),
            reply_markup=ReplyKeyboardMarkup([[BACK_BTN[lang]]], resize_keyboard=True),
        )
        return Q_AUTOBIO

    # boshqa narsa kelsa – xulosani qaytadan chiqaramiz
    await send_summary(update, context)
    return CONFIRM


async def done_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Resume to'ldirilgandan keyingi holat.
    - Agar user "Qayta to'ldirish" tugmasini bossachi: anketa boshidan boshlanadi.
    - Boshqa har qanday matn yozsa:
        * yozgan xabarini o'chirishga harakat qiladi
        * standart xabar + "Qayta to‘ldirish" tugmasini qaytadan yuboradi
    """
    lang = get_lang(context)
    text = (update.message.text or "").strip()
    restart_text = RESTART_BTN[lang]

    # Qayta to'ldirish tugmasi bosilsa
    if text == restart_text:
        context.user_data.clear()
        return await start(update, context)  # yana /start flow

    # Har qanday boshqa matn kelsa – o‘chirishga harakat qilamiz
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
        )
    except Exception:
        # agar ruxsat bo'lmasa – shunchaki e'tiborsiz
        pass

    final_msg = (
        "Adminlarimiz siz bilan tez orada bog‘lanishadi.\n\n"
        "Agar qandaydir savolingiz bo‘lsa, @ALLMAXHR bilan bog‘lanishingiz mumkin."
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=final_msg,
        reply_markup=ReplyKeyboardMarkup(
            [[restart_text]],
            resize_keyboard=True
        ),
    )

    return DONE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    context.user_data.clear()

    if lang == "uz":
        msg = "Jarayon bekor qilindi. /start orqali qayta boshlashingiz mumkin."
    elif lang == "ru":
        msg = "Процесс отменен. Вы можете начать заново с помощью /start."
    else:
        msg = "Process cancelled. You can start again with /start."

    await update.message.reply_text(
        msg,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ================== MAIN ==================

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_lang)],
            Q_AUTOBIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_autobio)],
            Q_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_address)],
            Q_PHONE: [
                MessageHandler(filters.CONTACT, q_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, q_phone),
            ],
            Q_EDU: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_edu)],
            Q_LANGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_langs)],
            Q_COMPUTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_computer)],
            Q_LASTJOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_lastjob)],
            Q_WHYJOB: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_whyjob)],
            Q_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_source)],
            Q_JOBGOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_jobgoal)],
            Q_CHARACTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_character)],
            Q_HIGHGOALS: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_highgoals)],
            Q_STRENGTHS: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_strengths)],
            Q_BOOKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_books)],
            Q_ACHIEVEMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_achievements)],
            Q_DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_department)],
            Q_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_role)],
            Q_SHIFT: [MessageHandler(filters.TEXT & ~filters.COMMAND, q_shift)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
            EDIT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_choice)],
            DONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, done_state)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)

    print("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
