"""
ALLMAX Community Agent — Claude-powered conversational auto-reply for Instagram DMs.

Arxitektura:
  - Caller (webhook) SQLite dan to'liq chat tarixini yig'adi
  - Bu modul faqat Claude API bilan ishlaydi
  - order_complete / needs_human tool-use orqali signal beradi
  - check_stock → moysklad.py orqali stok tekshiradi (agentic loop)
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import anthropic

from . import moysklad

log = logging.getLogger(__name__)

_TZ         = timedelta(hours=5)  # UTC+5 Toshkent
_WORK_START = int(os.getenv("COMMUNITY_WORK_START", "9"))
_WORK_END   = int(os.getenv("COMMUNITY_WORK_END",   "22"))
_ADDRESS    = os.getenv("COMMUNITY_ADDRESS",  "Toshkent sh., Bunyodkor Savdo Majmuasi (Korzinka -1-qavat, er osti qavat), metro: Mirzo Ulug'bek")
_PHONE      = os.getenv("COMMUNITY_PHONE",    "+998 78 555 31 31")

_BTS_COVERAGE: dict[str, list[str]] = {
    "Toshkent shahar": [
        "Yunusobod", "Chilonzor", "Mirzo Ulug'bek", "Shayxontohur",
        "Uchtepa", "Yakkasaroy", "Sergeli", "Olmazar", "Bektemir",
        "Yashnobod", "Mirobod",
    ],
    "Toshkent viloyati": [
        "Angren", "Bekobod", "Chirchiq", "Nurafshon", "Ohangaron",
        "Yangiyo'l", "Zangiota", "Qibray", "Oqqo'rg'on", "Bo'ka",
        "Parkent", "Piskent", "Yuqorichirchiq", "O'rta Chirchiq",
    ],
    "Samarqand viloyati": [
        "Samarqand", "Urgut", "Kattaqo'rg'on", "Ishtixon", "Pastdarg'om",
        "Bulung'ur", "Jomboy", "Qo'shrabot", "Nurobod",
    ],
    "Buxoro viloyati": [
        "Buxoro", "Kogon", "G'ijduvon", "Qorako'l", "Romitan",
        "Shofirkon", "Vobkent", "Jondor",
    ],
    "Namangan viloyati": [
        "Namangan", "Chust", "Pop", "Kosonsoy", "Uychi",
        "Mingbuloq", "Norin", "To'raqo'rg'on", "Chortoq",
    ],
    "Andijon viloyati": [
        "Andijon", "Asaka", "Xo'jaobod", "Marhamat", "Oltinko'l",
        "Shahrixon", "Baliqchi", "Buloqboshi", "Izboskan",
    ],
    "Farg'ona viloyati": [
        "Farg'ona", "Qo'qon", "Marg'ilon", "Rishton", "Beshariq",
        "Qo'shtepa", "Oltiariq", "Buvayda", "Dang'ara", "Uchko'prik",
    ],
    "Qashqadaryo viloyati": [
        "Qarshi", "Shahrisabz", "G'uzor", "Koson", "Muborak",
        "Kitob", "Chiroqchi", "Yakkabog'", "Kamashi",
    ],
    "Surxondaryo viloyati": [
        "Termiz", "Denov", "Sherobod", "Boysun", "Sariosiyo",
        "Qumqo'rg'on", "Uzun", "Jarqo'rg'on",
    ],
    "Xorazm viloyati": [
        "Urganch", "Xiva", "Shovot", "Bog'ot", "Qo'shko'pir",
        "Gurlan", "Hazorasp", "Yangiariq",
    ],
    "Jizzax viloyati": [
        "Jizzax", "Zomin", "G'allaorol", "Paxtakor", "Sharof Rashidov",
        "Arnasoy", "Baxmal", "Do'stlik",
    ],
    "Sirdaryo viloyati": [
        "Guliston", "Yangiyer", "Shirin", "Sardoba", "Boyovut",
        "Mirzaobod", "Oqoltin", "Sayxunobod",
    ],
    "Navoiy viloyati": [
        "Navoiy", "Zarafshon", "Uchquduq", "Karmana", "Nurota",
        "Konimex", "Navbahor", "Qiziltepa",
    ],
    "Qoraqalpog'iston": [
        "Nukus", "Turtkul", "Xo'jayli", "Beruniy", "Qo'ng'irot",
        "Chimboy", "Shumanay", "To'rtko'l",
    ],
}


def _bts_coverage_summary() -> str:
    lines = []
    for reg, districts in _BTS_COVERAGE.items():
        lines.append(f"  {reg}: {', '.join(districts)}")
    return "\n".join(lines)


_KNOWLEDGE = f"""
Do'kon manzili: {_ADDRESS}
Do'kon telefoni: {_PHONE}
Do'kon ish vaqti: 24/7 — yigirma to'rt soat, yetti kun (do'kon hech qachon yopilmaydi)
Call centre va community xodimlari: har kuni {_WORK_START:02d}:00 – {_WORK_END:02d}:00 (Toshkent vaqti)

Mahsulotlar (erkaklar uchun) — bu ro'yxat to'LIQ EMAS, doim check_stock bilan tekshir:
  Kiyim: kurtka, vetrovka, ko'ylak, polo, futbolka, shim, jinsi, kastyum-shim,
         kostyum, kashmir dvoyka, pidjak, jiletka, bezrukavka, mayka, sviter, kardigan
  Oyoq kiyim: loafers / mokasina, sneakers / krossovka, slides, tapochka, tufli, sapog
  Sumkalar: sumka, barsetka, yon sumka, bananka, ryukzak, chemodan, kartmon / hamyon
  Soatlar: qo'l soat (Rolex, Cartier, Patek Philippe va boshqa brendlar)
  Hidlar / atirlar: parfum, adekalon (atir so'ransa — check_stock("parfum") chaqir)
  Aksessuarlar: remen / kamar, ko'zoynak, galstuk, qo'lqop, paypoq, ro'molcha, zapinka
  Sport / sog'liq: bandaj, sport kiyimlari, koptok
  Boshqa: termos, ventilyator, fen, soch-soqol jihozlar, va boshqalar

MUHIM: Bu ro'yxatda YO'Q mahsulot ham do'konda MAVJUD bo'lishi mumkin.
Har doim check_stock bilan tekshir — taxmin qilma!

O'lchamlar: M–3XL (kattaroq ham bor); shimlarda 29–56

Narxlar (fix-price bo'limlari):
  • 99 000 so'm
  • 149 900 so'm
  • 199 900 so'm
  • 249 900 so'm
  • 299 900 so'm
  • Premium bo'lim — alohida narxlar

To'lov: naqd, plastik karta, Uzum nasiya (bo'lib to'lash)

Yetkazib berish:
  • Toshkent shahri ichida — YandexGo orqali (mijoz manziliga)
  • Butun O'zbekiston bo'ylab — BTS, EMU yoki UzPost orqali

Almashtirish/qaytarish: mumkin (batafsil operator aytadi)
"""

SYSTEM_PROMPT = f"""Sen ALLMAX erkaklar kiyim do'konining onlayn Community Agent-isan.
Senga Instagram orqali kelgan DM suhbatini to'liq tahlil qilib, davom ettirishni so'rashadi.

ALLMAX haqida:
{_KNOWLEDGE}

STOK QOIDASI — ENG MUHIM (HECH QACHON BUZMA):
Mijoz biror mahsulot so'raganda — suhbat tarixida qanday javob berilgan bo'lishidan QATI NAZAR —
DOIM check_stock tool chaqirilishi SHART.

MUHIM: Suhbat tarixidagi barcha mahsulot mavjudligi haqidagi javoblar NOTO'G'RI BO'LISHI MUMKIN.
Tarixdagi "bor" yoki "yo'q" javoblariga HECH QACHON ishonma — har doim yangi check_stock chaqir.
Stok har kuni, har soat o'zgaradi. Faqat check_stock natijasi to'g'ri hisoblanadi.

ASOSIY QOIDALAR:
1. Mahsulot savoli → DOIM check_stock (tarixdan qat'i nazar)
2. Buyurtmani faqat operator tasdiqlaydi — sen faqat ma'lumot yig'asan
3. Mijoz qaysi tilda yozsa, SHU tilda javob ber (O'zbek / Rus / Ingliz)
4. Samimiy, muloyim, professional — robotday EMAS
5. Emoji: 1–2 tadan oshirma
6. Qisqa va aniq javob ber
7. Suhbat tarixida avval berilgan BOSHQA javoblarni qayta berma — kontekstni esda tut

KONTEKST TAHLILI:
Senga berilgan suhbat tarixida:
  - "user" xabarlari → mijoz tomonidan (Instagram DM)
  - "assistant" xabarlari → Allmax (sen) tomonidan yoki operator tomonidan
  - Rasm yuborilsa → kontekstga qarab javob ber

Avvalgi javoblarni ko'rib, takrorlanmaslik uchun davom et.
LEKIN: tarixdagi mahsulot mavjudligi haqidagi javoblar ESKIRGAN bo'lishi mumkin — qayta check_stock chaqir.

XABAR TURLARI VA HARAKAT:

A) STANDART SAVOLLAR (o'zing javob ber):
   manzil    → aniq ayt: {_ADDRESS}
   narx      → bo'limlarni sanab ayt: 99 000 / 149 900 / 199 900 / 249 900 / 299 900 / Premium
   o'lcham   → mavjud o'lchamlar (M–3XL, shimlarda 29–56)
   dostavka  → Toshkent shahri: YandexGo | Boshqa: BTS/EMU/UzPost
   almashtirish → mumkin, batafsil operator aytadi
   ish vaqti → DO'KON 24/7 ishlaydi; call centre va community 09:00–22:00

A2) MAHSULOT BOR/YO'Q SAVOLI — check_stock tool chaqir (HECH QACHON O'ZIN JAVOB BERMA):
   Misol savollar: "polo bormi?", "soat bormi?", "atir bormi?", "barsetka bormi?"
   → check_stock(query="[mahsulot nomi]") chaqir, natijani mijozga ko'rsat
   → Agar bor: narxini ham ayt
   → Agar yo'q: "Afsuski hozir tugagan, yangi kelishi bilanoq xabar beramiz" de

   MUHIM SYNONYM QOIDALARI:
   • "atir", "parfum" → check_stock("parfum") chaqir
   • "soat", "часы" → check_stock("soat") chaqir
   • "barsetka" → check_stock("barsetka") chaqir
   • "bandaj" → check_stock("bandaj") chaqir

B) BUYURTMA — ma'lumotlarni natural suhbat orqali yig':
   Kerakli 9 ta ma'lumot (tabiiy ketma-ketlikda so'ra):
     1) ism
     2) telefon raqami
     3) qaysi mahsulot (nomi yoki tavsifi)
     4) razmer / o'lcham
     5) rang
     6) soni
     7) viloyat / shahar
        ↳ Agar TOSHKENT SHAHRI: "YandexGo orqali yetkazib beramiz. Manzilingizni yozing."
           → postal = "YandexGo", tuman = manzil
        ↳ Boshqa viloyat → 8 va 9-bandlarga o't
     8) tuman
     9) qulay pochta: BTS, EMU yoki UzPost

   Bir yo'la hammani so'rama — 1–2 tadan tabiiy so'ra.
   Suhbat tarixida allaqachon so'ralgan ma'lumotni qaytadan so'rma.

BTS QOPLAM RO'YXATI:
{_bts_coverage_summary()}

C) BARCHA MA'LUMOT TO'LIQ BO'LGACH:
   order_complete tool chaqir.
   Keyin mijozga:
     ish vaqtida ({_WORK_START}:00–{_WORK_END}:00): "Operatorimiz 5–10 daqiqada siz bilan bog'lanadi"
     ish vaqtidan tashqarida: "Ertalab {_WORK_START}:30 dan operatorimiz siz bilan bog'lanadi"

D) MURAKKAB / NOANIQ SAVOLLAR:
   needs_human tool chaqir.
   Mijozga: "Operatorimizga yo'naltirdim, tez orada bog'lanishadi"
"""

_TOOLS = [
    {
        "name": "order_complete",
        "description": "Buyurtma uchun barcha ma'lumotlar to'liq yig'ilganda chaqiriladi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":     {"type": "string",  "description": "Mijoz ismi"},
                "phone":    {"type": "string",  "description": "Telefon raqami"},
                "product":  {"type": "string",  "description": "Mahsulot nomi/tavsifi"},
                "size":     {"type": "string",  "description": "O'lcham/razmer"},
                "color":    {"type": "string",  "description": "Rang"},
                "qty":      {"type": "integer", "description": "Soni"},
                "region":   {"type": "string",  "description": "Viloyat yoki shahar"},
                "district": {"type": "string",  "description": "Tuman yoki manzil"},
                "postal":   {"type": "string",  "description": "Yetkazish usuli: BTS / EMU / UzPost / YandexGo"},
            },
            "required": ["name", "phone", "product", "size", "region", "district", "postal"],
        },
    },
    {
        "name": "needs_human",
        "description": "Savol murakkab yoki agent javob bera olmasa — operator kerak.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Nima uchun operator kerak (qisqa)"},
            },
            "required": ["reason"],
        },
    },
    {
        "name": "check_stock",
        "description": (
            "Mahsulot omborda borligini va narxini tekshiradi. "
            "Mijoz 'X bormi?', 'X qolganmi?', 'X narxi qancha?' desa chaqir."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Qidiruv so'zi (masalan: 'polo', 'kurtka XL', 'qora shim')",
                },
            },
            "required": ["query"],
        },
    },
]


def _work_msg() -> str:
    h = (datetime.now(timezone.utc) + _TZ).hour
    if _WORK_START <= h < _WORK_END:
        return "Operatorimiz 5–10 daqiqada siz bilan bog'lanadi ✅"
    return f"Ertalab {_WORK_START}:30 dan operatorimiz siz bilan bog'lanadi 🕘"


def _to_content_list(c) -> list:
    if isinstance(c, list):
        return list(c)
    return [{"type": "text", "text": str(c)}]


def _merge_consecutive(messages: list[dict]) -> list[dict]:
    if not messages:
        return []
    merged = [dict(messages[0])]
    for msg in messages[1:]:
        last = merged[-1]
        if msg["role"] == last["role"]:
            merged[-1] = {
                "role": last["role"],
                "content": _to_content_list(last["content"]) + _to_content_list(msg["content"]),
            }
        else:
            merged.append(dict(msg))
    return merged


def build_claude_messages(history: list[dict]) -> list[dict]:
    """SQLite history_json ni Claude API formatiga o'giradi (image blocks bilan)."""
    messages = []
    for item in history:
        role = item.get("role", "")
        text = (item.get("text") or "").strip()
        if role == "incoming":
            content_blocks: list[dict] = list(item.get("content_blocks") or [])
            if content_blocks:
                blocks: list[dict] = []
                if text:
                    blocks.append({"type": "text", "text": text})
                blocks.extend(content_blocks)
                messages.append({"role": "user", "content": blocks})
            elif text:
                messages.append({"role": "user", "content": text})
        elif role in ("outgoing", "outgoing_sync"):
            if text:
                messages.append({"role": "assistant", "content": text})
    return messages


@dataclass
class AgentResult:
    reply: str = ""
    order_data: Optional[dict] = None
    needs_human: bool = False
    human_reason: str = ""


class CommunityAgent:
    def __init__(self, api_key: str, model: str = "claude-opus-4-8"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model  = model

    def process(self, messages: list[dict]) -> AgentResult:
        """
        messages: Claude API formatidagi to'liq suhbat tarixi.
        check_stock tool uchun agentic loop (maks 4 iteratsiya).
        Synchronous — thread pool da chaqiriladi.
        """
        if not messages:
            messages = [{"role": "user", "content": "Salom"}]

        prepared = _merge_consecutive(messages)

        while prepared and prepared[0]["role"] == "assistant":
            prepared.pop(0)
        while prepared and prepared[-1]["role"] == "assistant":
            prepared.pop()
        if not prepared:
            prepared = [{"role": "user", "content": "Salom"}]

        current = list(prepared)
        parts: list[str] = []
        order_data = None
        needs_human = False
        human_reason = ""

        for _iteration in range(4):
            try:
                resp = self._client.messages.create(
                    model=self._model,
                    max_tokens=1200,
                    system=SYSTEM_PROMPT,
                    tools=_TOOLS,
                    messages=current,
                )
            except anthropic.RateLimitError as e:
                log.warning("Claude rate limit: %s", e)
                return AgentResult(reply="Tizimda vaqtinchalik muammo, biroz kutib qayta yozing 🙏")
            except anthropic.APIError as e:
                log.error("Claude API xatosi: %s", e)
                return AgentResult(reply="Tizimda muammo yuz berdi 🙏")
            except Exception as e:
                log.exception("Claude kutilmagan xato: %s", e)
                return AgentResult(reply="Tizimda muammo yuz berdi 🙏")

            tool_calls = [b for b in resp.content if b.type == "tool_use"]
            stock_calls = [b for b in tool_calls if b.name == "check_stock"]

            if not stock_calls:
                for block in resp.content:
                    if block.type == "text":
                        t = (block.text or "").strip()
                        if t:
                            parts.append(t)
                    elif block.type == "tool_use":
                        if block.name == "order_complete":
                            order_data = dict(block.input)
                            parts.append(_work_msg())
                        elif block.name == "needs_human":
                            needs_human  = True
                            human_reason = (block.input or {}).get("reason", "")
                            parts.append("Operatorimizga yo'naltirdim, tez orada bog'lanishadi 🙏")
                break

            tool_results = []
            for tc in stock_calls:
                query = (tc.input or {}).get("query", "")
                log.info("MoySklad stok qidiruvi: %s", query)
                try:
                    results = moysklad.check_stock(query)
                    result_text = moysklad.format_stock_reply(results, query)
                except Exception as exc:
                    log.warning("moysklad.check_stock xatosi: %s", exc)
                    result_text = "Stok ma'lumotini olishda xatolik yuz berdi."
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": tc.id,
                    "content":     result_text,
                })

            current = current + [
                {"role": "assistant", "content": list(resp.content)},
                {"role": "user",      "content": tool_results},
            ]

        reply = "\n\n".join(parts).strip()
        return AgentResult(
            reply=reply,
            order_data=order_data,
            needs_human=needs_human,
            human_reason=human_reason,
        )
