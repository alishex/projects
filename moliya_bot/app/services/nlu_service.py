import logging

from anthropic import AsyncAnthropic, APIStatusError

from app.config import ANTHROPIC_API_KEY, NLU_MODEL
from app.categories import EXPENSE_CATEGORIES, INCOME_CATEGORIES

log = logging.getLogger(__name__)

_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

_EXPENSE_CODES = [c for c, _ in EXPENSE_CATEGORIES]
_INCOME_CODES = [c for c, _ in INCOME_CATEGORIES]

_TOOL = {
    "name": "record_transaction",
    "description": "Эркин матндан (харажат ёки даромад ҳақида) структураланган маълумот чиқариш",
    "input_schema": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["expense", "income"]},
            "amount": {"type": "number", "description": "Миқдор, валюта белгисисиз"},
            "currency": {"type": "string", "enum": ["UZS", "USD"]},
            "method": {"type": "string", "enum": ["cash", "card"]},
            "category": {"type": "string", "enum": _EXPENSE_CODES + _INCOME_CODES},
            "comment": {"type": "string", "description": "Қисқа изоҳ, матндан олинган"},
            "needs_clarification": {
                "type": "boolean",
                "description": "Миқдор ёки тур аниқ бўлмаса true",
            },
        },
        "required": ["kind", "amount", "currency", "method", "category", "needs_clarification"],
    },
}

_SYSTEM = (
    "Сен молиявий трекер ботининг ёрдамчисисан. Фойдаланувчи эркин ўзбек тилида "
    "ёзган/айтган хабарни таҳлил қилиб, record_transaction toolини чақир.\n"
    f"Харажат категориялари: {', '.join(_EXPENSE_CODES)}\n"
    f"Даромад категориялари: {', '.join(_INCOME_CODES)}\n"
    "Агар тўлов усули (нақд/карта) матнда аниқ айтилмаса — method='cash' деб ол, "
    "лекин needs_clarification=true қўй.\n"
    "Агар миқдор ёки тур тушунарсиз бўлса — тахмин қилма, needs_clarification=true қўй."
)


async def parse_free_text(text: str):
    """Natija: dict (muvaffaqiyatli tahlil), None (kalit sozlanmagan) yoki 'error' (API xatosi)."""
    if _client is None:
        return None
    try:
        resp = await _client.messages.create(
            model=NLU_MODEL,
            max_tokens=512,
            system=_SYSTEM,
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "record_transaction"},
            messages=[{"role": "user", "content": text}],
        )
        for block in resp.content:
            if block.type == "tool_use":
                return block.input
        return "error"
    except APIStatusError as e:
        log.error("Anthropic API xatosi (ehtimol balans tugagan): %s", e)
        return "error"
    except Exception:
        log.exception("NLU tahlilida kutilmagan xato")
        return "error"
