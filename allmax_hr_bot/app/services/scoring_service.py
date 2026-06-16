def grade_from_score(score: int) -> str:
    if score < 60:
        return "low"
    if score < 80:
        return "medium"
    return "excellent"


def grade_label(grade: str | None) -> str:
    return {"low": "Past baho", "medium": "O‘rta baho", "excellent": "A’lo baho"}.get(grade or "", "Noma’lum")
