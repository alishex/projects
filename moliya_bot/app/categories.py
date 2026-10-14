EXPENSE_CATEGORIES = [
    ("food", "🍽 Озиқ-овқат"),
    ("transport", "🚗 Транспорт"),
    ("housing", "🏠 Уй-жой"),
    ("health", "💊 Соғлиқ"),
    ("education", "📚 Таълим"),
    ("clothes", "👗 Кийим-кечак"),
    ("fun", "🎮 Ўйин-кулги"),
    ("communication", "📞 Коммуникация"),
    ("family", "👨‍👩‍👧 Оила"),
    ("savings", "💰 Жамғарма"),
    ("other_expense", "📦 Бошқа"),
]

INCOME_CATEGORIES = [
    ("salary", "💼 Иш ҳақи"),
    ("side_job", "📊 Қўшимча иш"),
    ("rent", "🏢 Ижара"),
    ("bonus", "🏆 Мукофот"),
    ("other_income", "📦 Бошқа даромад"),
]


def category_label(kind: str, code: str) -> str:
    source = EXPENSE_CATEGORIES if kind == "expense" else INCOME_CATEGORIES
    for c, label in source:
        if c == code:
            return label
    return code
