"""Stable domain constants used across handlers and services."""
from __future__ import annotations

EMPLOYEE_ROLES = [
    "SMM Manager",
    "Brandface",
    "Community Manager",
    "Graphic Designer #1",
    "Graphic Designer #2",
    "Mobilograf #1",
    "Mobilograf #2",
    "Stories Maker",
    "IT Systems Employee",
]

PRIORITIES = {
    "P1": {"label": "Muhim va shoshilinch", "button": "🔴 Muhim va shoshilinch — Hozir bajarish", "icon": "🔴", "score": 400},
    "P2": {"label": "Muhim, lekin shoshilinch emas", "button": "🟡 Muhim, lekin shoshilinch emas — Rejalashtirish", "icon": "🟡", "score": 300},
    "P3": {"label": "Muhim emas, lekin shoshilinch", "button": "🟠 Muhim emas, lekin shoshilinch — Tez bajarish", "icon": "🟠", "score": 200},
    "P4": {"label": "Muhim emas va shoshilinch emas", "button": "⚪ Muhim emas va shoshilinch emas — Keyinroq bajarish", "icon": "⚪", "score": 100},
}

ACTIVE_STATUSES = ("ACTIVE", "OVERDUE")
ALL_STATUSES = (
    "DRAFT", "WAITING_EMPLOYEE_DEADLINE", "WAITING_ADMIN_APPROVAL",
    "ACTIVE", "COMPLETED", "OVERDUE", "CANCELLED",
)

STATUS_LABELS = {
    "DRAFT": "Qoralama",
    "WAITING_EMPLOYEE_DEADLINE": "Xodim deadline taklif qilishi kutilmoqda",
    "WAITING_ADMIN_APPROVAL": "Admin tasdig‘i kutilmoqda",
    "ACTIVE": "Jarayonda",
    "COMPLETED": "Tugatilgan",
    "OVERDUE": "Kechikkan",
    "CANCELLED": "Bekor qilingan",
}

UNAUTHORIZED_MESSAGE = "Bu bot faqat egasi uchun ishlaydi."
DEADLINE_FORMAT = "%d.%m.%Y %H:%M"
