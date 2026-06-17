"""
ALLMAX Community Agent — Claude-powered conversational auto-reply for Telegram DMs.

Arxitektura:
  - Caller (main_ready_project) to'liq chat tarixini yig'adi (matn + transkriptsiya + rasmlar)
  - Bu modul faqat Claude API bilan ishlaydi
  - order_complete / needs_human tool-use orqali signal beradi
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import anthropic

log = logging.getLogger(__name__)

_TZ         = timedelta(hours=5)  # UTC+5 Toshkent
_WORK_START = int(os.getenv("COMMUNITY_WORK_START", "9"))
_WORK_END   = int(os.getenv("COMMUNITY_WORK_END",   "22"))
_ADDRESS    = os.getenv("COMMUNITY_ADDRESS",  "Toshkent sh., Bunyodkor Savdo Majmuasi (Korzinka 1-qavat), metro: Mirzo Ulug'bek")
_PHONE      = os.getenv("COMMUNITY_PHONE",    "+998 78 555 31 31")

_KNOWLEDGE = f"""
Do'kon manzili: {_ADDRESS}
Do'kon telefoni: {_PHONE}
Ish vaqti: har kuni {_WORK_START:02d}:00 – {_WORK_END:02d}:00 (Toshkent vaqti, UTC+5)

Mahsulotlar (erkaklar uchun):
  kurtka, vetrovka, ko'ylak, polo, futbolka, shim, jinsi, kastyum-shim,
  kostyum, kashmir dvoyka, oyoq kiyim (loafers / sneakers / slides / tapochka),
  remen, hamyon, sumka, aksessuarlar

O'lchamlar: M–3XL (kattaroq ham bor); shimlarda 29–56
Narxlar (fix-price): 99 900 – 399 900 so'm
To'lov: naqd, plastik karta, Uzum nasiya (bo'lib to'lash)
Dostavka: O'zbekiston bo'ylab — BTS, EMU yoki UzPost orqali
Almashtirish/qaytarish: mumkin (batafsil operator aytadi)
"""

SYSTEM_PROMPT = f"""Sen ALLMAX erkaklar kiyim do'konining onlayn Community Agent-isan.
Senga Telegram orqali kelgan DM suhbatini to'liq tahlil qilib, davom ettirishni so'rashadi.

ALLMAX haqida:
{_KNOWLEDGE}

ASOSIY QOIDALAR (HECH QACHON BUZMA):
1. Mahsulot bor yoki yo'qligi haqida ASLO o'zing qaror qilma
2. Buyurtmani faqat operator tasdiqlaydi — sen faqat ma'lumot yig'asan
3. Faqat O'ZBEK tilida gapir
4. Samimiy, muloyim, professional — robotday EMAS
5. Emoji: 1–2 tadan oshirma
6. Qisqa va aniq javob ber
7. Agar suhbatda avval javob berilgan savolni qayta bermaslik kerak — kontekstni esda tut

KONTEKST TAHLILI:
Senga berilgan suhbat tarixida:
  - "user" xabarlari → mijoz tomonidan
  - "assistant" xabarlari → Allmax (sen) tomonidan yoki operator tomonidan
  - [🎤 Ovozli xabar: ...] → mijoz ovozli xabar yuborgan, transkripsiya ko'rsatilgan
  - [🎥 Video xabar: ...] → video xabar transkripsiyasi
  - [Rasm] yoki rasm bloki → mijoz rasm yuborgan

Avvalgi javoblarni ko'rib, takrorlanmaslik uchun davom et.

XABAR TURLARI VA HARAKAT:

A) STANDART SAVOLLAR (o'zing javob ber):
   manzil → aniq ayt | ish vaqti → ayt | narx → diapazon (99 900–399 900)
   o'lcham → mavjud o'lchamlar | dostavka → bor, pochta tanlash mumkin
   almashtirish → mumkin, batafsil operator aytadi

B) BUYURTMA — ma'lumotlarni natural suhbat orqali yig':
   Kerakli 9 ta ma'lumot (tabiiy ketma-ketlikda so'ra):
     1) ism
     2) telefon raqami
     3) qaysi mahsulot (nomi yoki tavsifi)
     4) razmer / o'lcham
     5) rang
     6) soni
     7) viloyat
     8) tuman (kerakli bo'lsa o'sha tumandagi pochta punktlarini tashla)
     9) qulay pochta: BTS, EMU yoki UzPost

   ⚠ Bir yo'la hammani so'rama — 1–2 tadan tabiiy so'ra.
   ⚠ Suhbat tarixida allaqachon so'ralgan ma'lumotni qaytadan so'rma.

C) BARCHA 9 TA MA'LUMOT TO'LIQ BO'LGACH:
   order_complete tool chaqir.
   Keyin mijozga:
     ish vaqtida ({_WORK_START}:00–{_WORK_END}:00): "Operatorimiz 5–10 daqiqada siz bilan bog'lanadi ✅"
     ish vaqtidan tashqarida: "Ertalab {_WORK_START}:30 dan operatorimiz siz bilan bog'lanadi 🕘"

D) MURAKKAB / NOANIQ SAVOLLAR:
   needs_human tool chaqir.
   Mijozga: "Operatorimizga yo'naltirdim, tez orada bog'lanishadi 🙏"

E) RASM YUBORILSA:
   Rasmni ko'r, nima ekanligini tushun, kontekstga qarab javob ber.
   Mahsulot rangi, o'lchami so'ralgandek bo'lsa — buyurtma oqimiga qo'sh.
"""

_TOOLS = [
    {
        "name": "order_complete",
        "description": "Buyurtma uchun barcha 9 ta ma'lumot (ism, telefon, mahsulot, razmer, rang, soni, viloyat, tuman, pochta) to'liq yig'ilganda chaqiriladi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name":     {"type": "string",  "description": "Mijoz ismi"},
                "phone":    {"type": "string",  "description": "Telefon raqami"},
                "product":  {"type": "string",  "description": "Mahsulot nomi/tavsifi"},
                "size":     {"type": "string",  "description": "O'lcham/razmer"},
                "color":    {"type": "string",  "description": "Rang"},
                "qty":      {"type": "integer", "description": "Soni"},
                "region":   {"type": "string",  "description": "Viloyat"},
                "district": {"type": "string",  "description": "Tuman"},
                "postal":   {"type": "string",  "description": "Pochta xizmati (BTS / EMU / UzPost)"},
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
]


def _work_msg() -> str:
    h = (datetime.now(timezone.utc) + _TZ).hour
    if _WORK_START <= h < _WORK_END:
        return "Operatorimiz 5–10 daqiqada siz bilan bog'lanadi ✅"
    return f"Ertalab {_WORK_START}:30 dan operatorimiz siz bilan bog'lanadi 🕘"


def _merge_consecutive(messages: list[dict]) -> list[dict]:
    """Bir-biriga ketma-ket bir xil role xabarlarni birlashtiradi (Claude talabi)."""
    if not messages:
        return []
    merged = [dict(messages[0])]
    for msg in messages[1:]:
        last = merged[-1]
        if msg["role"] == last["role"]:
            # Ikkalasini list formatiga o'tkazib birlashtirish
            def to_list(c):
                if isinstance(c, list):
                    return c
                return [{"type": "text", "text": str(c)}]
            merged[-1] = {"role": last["role"], "content": to_list(last["content"]) + to_list(msg["content"])}
        else:
            merged.append(dict(msg))
    return merged


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
        Caller (main) Telegram DM tarixini build qilib beradi.
        Synchronous — asyncio.to_thread() orqali chaqirilsin.
        """
        if not messages:
            messages = [{"role": "user", "content": "Salom"}]

        # Consecutive merge (Claude talabi)
        prepared = _merge_consecutive(messages)

        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=1200,
                system=SYSTEM_PROMPT,
                tools=_TOOLS,
                messages=prepared,
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

        parts: list[str] = []
        order_data = None
        needs_human = False
        human_reason = ""

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

        reply = "\n\n".join(parts).strip()
        return AgentResult(
            reply=reply,
            order_data=order_data,
            needs_human=needs_human,
            human_reason=human_reason,
        )
