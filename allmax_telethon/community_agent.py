"""
ALLMAX Community Agent — Claude-powered conversational auto-reply for Telegram DMs.

Arxitektura:
  - Caller (main_ready_project) to'liq chat tarixini yig'adi (matn + transkriptsiya + rasmlar)
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
import moysklad

log = logging.getLogger(__name__)

_TZ         = timedelta(hours=5)  # UTC+5 Toshkent
_WORK_START = int(os.getenv("COMMUNITY_WORK_START", "9"))
_WORK_END   = int(os.getenv("COMMUNITY_WORK_END",   "22"))
_ADDRESS    = os.getenv("COMMUNITY_ADDRESS",  "Toshkent sh., Bunyodkor Savdo Majmuasi (Korzinka 1-qavat), metro: Mirzo Ulug'bek")
_PHONE      = os.getenv("COMMUNITY_PHONE",    "+998 78 555 31 31")

# BTS filiallar qoplami (viloyat → tumanlar ro'yxati)
# ESLATMA: Bu ro'yxat taxminiy. Aniq ma'lumot uchun BTS rasmiy saytini tekshiring.
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


def _bts_check(region: str, district: str) -> tuple[bool, str]:
    """(mavjud, xabar) qaytaradi."""
    r_low = region.strip().lower()
    d_low = district.strip().lower()
    for reg, districts in _BTS_COVERAGE.items():
        if r_low in reg.lower() or reg.lower() in r_low:
            for d in districts:
                if d_low in d.lower() or d.lower() in d_low:
                    return True, f"BTS filiali {reg} — {d} tumanida mavjud"
            return False, f"BTS {reg}da {district} tumanini qoplamaydi (yirik shahar markaziga yetkazilishi mumkin)"
    return False, f"BTS {region} viloyati bo'yicha ma'lumot yo'q"


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

Mahsulotlar (erkaklar uchun):
  kurtka, vetrovka, ko'ylak, polo, futbolka, shim, jinsi, kastyum-shim,
  kostyum, kashmir dvoyka, oyoq kiyim (loafers / sneakers / slides / tapochka),
  remen, hamyon, sumka, aksessuarlar

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
Senga Telegram orqali kelgan DM suhbatini to'liq tahlil qilib, davom ettirishni so'rashadi.

ALLMAX haqida:
{_KNOWLEDGE}

ASOSIY QOIDALAR (HECH QACHON BUZMA):
1. Mahsulot bor yoki yo'qligi haqida ASLO o'zing taxmin qilma — check_stock tool chaqir
2. Buyurtmani faqat operator tasdiqlaydi — sen faqat ma'lumot yig'asan
3. Mijoz qaysi tilda yozsa, SHU tilda javob ber (O'zbek / Rus / Ingliz)
4. Samimiy, muloyim, professional — robotday EMAS
5. Emoji: 1–2 tadan oshirma
6. Qisqa va aniq javob ber
7. Suhbat tarixida avval berilgan javobni qayta berma — kontekstni esda tut

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
   manzil    → aniq ayt
   narx      → bo'limlarni sanab ayt: 99 000 / 149 900 / 199 900 / 249 900 / 299 900 / Premium
   o'lcham   → mavjud o'lchamlar (M–3XL, shimlarda 29–56)
   dostavka  → Toshkent shahri: YandexGo | Boshqa: BTS/EMU/UzPost
   almashtirish → mumkin, batafsil operator aytadi
   ish vaqti → DO'KON 24/7 ishlaydi; call centre va community 09:00–22:00

A2) MAHSULOT BOR/YO'Q SAVOLI — check_stock tool chaqir:
   Misol savollar: "polo bormi?", "XL kurtka bormi?", "qora shim bormi?", "shu mahsulot bormi?"
   → check_stock(query="polo") chaqir, natijani mijozga ko'rsat
   → Agar bor: narxini ham ayt
   → Agar yo'q: "Afsuski hozir tugagan, yangi kelishi bilanoq xabar beramiz" de

B) BUYURTMA — ma'lumotlarni natural suhbat orqali yig':
   Kerakli 9 ta ma'lumot (tabiiy ketma-ketlikda so'ra):
     1) ism
     2) telefon raqami
     3) qaysi mahsulot (nomi yoki tavsifi)
     4) razmer / o'lcham
     5) rang
     6) soni
     7) viloyat / shahar
        ↳ Agar TOSHKENT SHAHRI: "Toshkent shahriga YandexGo orqali yetkazib beramiz.
           Manzilingizni (ko'cha, uy) yozing, operatorimiz vaqtni kelishib oladi 🚗"
           → postal = "YandexGo" bo'ladi, tuman = manzil bo'ladi
        ↳ Boshqa viloyat → 8 va 9-bandlarga o't
     8) tuman
        ↳ BTS tanlansa: quyidagi BTS qoplam ro'yxatini tekshir.
          * Tuman ro'yxatda BOR → "Shu tumanda BTS filiali bor, shu yerga yetkazib bersak ma'qulmi? ✅"
          * Tuman ro'yxatda YO'Q → "Afsuski BTS [tuman]ni qoplamaydi. EMU yoki UzPost tanlasangiz bo'ladi."
        ↳ EMU/UzPost tanlansa: tumanini so'ra, davom et
     9) qulay pochta: BTS, EMU yoki UzPost
        (Toshkent shahri uchun bu qadam o'tkazib yuboriladi — YandexGo)

   ⚠ Bir yo'la hammani so'rama — 1–2 tadan tabiiy so'ra.
   ⚠ Suhbat tarixida allaqachon so'ralgan ma'lumotni qaytadan so'rma.

BTS QOPLAM RO'YXATI (tumanlar bo'yicha):
{_bts_coverage_summary()}

C) BARCHA MA'LUMOT TO'LIQ BO'LGACH:
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
                "district": {"type": "string",  "description": "Tuman yoki manzil (Toshkent uchun)"},
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


def _strip_images_from_assistant(messages: list[dict]) -> list[dict]:
    """Claude API assistant turnida image block ruxsat bermaydi — birini ham o'tkazmaydi."""
    out = []
    for msg in messages:
        if msg["role"] != "assistant" or not isinstance(msg.get("content"), list):
            out.append(msg)
            continue
        clean = [b for b in msg["content"] if b.get("type") != "image"]
        if not clean:
            clean = [{"type": "text", "text": "[media]"}]
        out.append({"role": "assistant", "content": clean if len(clean) > 1 else clean[0]["text"]})
    return out


def _merge_consecutive(messages: list[dict]) -> list[dict]:
    """Bir-biriga ketma-ket bir xil role xabarlarni birlashtiradi (Claude talabi)."""
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

        check_stock tool uchun agentic loop (maks 3 iteratsiya):
          1) Claude check_stock chaqiradi
          2) Biz moysklad.check_stock() bajaramiz
          3) Natijani tool_result sifatida qaytaramiz
          4) Claude mijozga javob beradi
        """
        if not messages:
            messages = [{"role": "user", "content": "Salom"}]

        prepared = _merge_consecutive(messages)
        prepared = _strip_images_from_assistant(prepared)

        while prepared and prepared[0]["role"] == "assistant":
            prepared.pop(0)
        if not prepared:
            prepared = [{"role": "user", "content": "Salom"}]

        current = list(prepared)
        parts: list[str] = []
        order_data = None
        needs_human = False
        human_reason = ""

        for _iteration in range(4):  # maks 4 iteratsiya (3 check_stock + 1 final)
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

            # Tool call larni ajratib olish
            tool_calls = [b for b in resp.content if b.type == "tool_use"]
            stock_calls = [b for b in tool_calls if b.name == "check_stock"]

            # check_stock bo'lmasa yoki terminal tool bo'lsa — tugatamiz
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

            # check_stock tool larini bajaramiz
            tool_results = []
            for tc in stock_calls:
                query = (tc.input or {}).get("query", "")
                log.info("MoySklad stok qidiruvi: %s", query)
                try:
                    results = moysklad.check_stock(query)
                    result_text = moysklad.format_stock_reply(results, query)
                except Exception as exc:
                    log.warning("moysklad.check_stock xatosi: %s", exc)
                    result_text = f"Stok ma'lumotini olishda xatolik yuz berdi."
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": tc.id,
                    "content":     result_text,
                })

            # Navbatdagi iteratsiya uchun xabarlar ro'yxatiga qo'shamiz
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
