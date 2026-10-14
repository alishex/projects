import logging

from anthropic import Anthropic, APIError

from app.config import ANTHROPIC_API_KEY, CLAUDE_COACH_MODEL, CLAUDE_FAST_MODEL

logger = logging.getLogger(__name__)
_client = Anthropic(api_key=ANTHROPIC_API_KEY)


class CoachUnavailable(Exception):
    pass

FOOD_PARSE_TOOL = {
    "name": "record_nutrition",
    "description": "Taom tavsifidan taxminiy ozuqa qiymatlarini qaytaradi",
    "input_schema": {
        "type": "object",
        "properties": {
            "calories": {"type": "number", "description": "Taxminiy umumiy kaloriya (kcal)"},
            "protein_g": {"type": "number", "description": "Oqsil miqdori (gramm)"},
            "carbs_g": {"type": "number", "description": "Uglevod miqdori (gramm)"},
            "fat_g": {"type": "number", "description": "Yog' miqdori (gramm)"},
        },
        "required": ["calories", "protein_g", "carbs_g", "fat_g"],
    },
}


def estimate_nutrition(description: str) -> dict:
    empty = {"calories": None, "protein_g": None, "carbs_g": None, "fat_g": None}
    try:
        response = _client.messages.create(
            model=CLAUDE_FAST_MODEL,
            max_tokens=300,
            tools=[FOOD_PARSE_TOOL],
            tool_choice={"type": "tool", "name": "record_nutrition"},
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Quyidagi taom tavsifi uchun taxminiy ozuqaviy qiymatlarni hisobla "
                        f"(O'zbekiston taomlariga xos odatiy porsiyalarni hisobga ol): {description}"
                    ),
                }
            ],
        )
    except APIError:
        logger.exception("Claude nutrition estimate failed; saving food log without AI values")
        return empty
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_nutrition":
            return block.input
    return empty


def coach_reply(history: list[dict], context_summary: str) -> str:
    system_prompt = (
        "Sen 'Ozish' fitnes ilovasidagi shaxsiy AI murabbiysan. Foydalanuvchiga vazn "
        "yo'qotishda samimiy, qisqa va amaliy maslahatlar ber. Tibbiy tashxis qo'yma, "
        "og'ir yoki shubhali holatlarda shifokorga murojaat qilishni tavsiya qil. "
        "Javoblarni o'zbek tilida, odatda 3-5 jumlada ber.\n\n"
        f"Foydalanuvchining so'nggi ma'lumotlari:\n{context_summary}"
    )
    try:
        response = _client.messages.create(
            model=CLAUDE_COACH_MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=history,
        )
    except APIError as exc:
        logger.exception("Claude coach reply failed")
        raise CoachUnavailable() from exc
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip()
