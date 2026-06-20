import asyncio
import json
import logging

from anthropic import Anthropic

import config
from telegram_client import TelegramToolset

logger = logging.getLogger("telegram_ai_assistant.agent")

SYSTEM_PROMPT = """Sen foydalanuvchining shaxsiy AI yordamchisan. Ikki turdagi vazifani bajarasan:

A) Telegram akkountini boshqarish: senga berilgan vositalar (tools) orqali foydalanuvchining
   barcha guruhlari, kanallari va shaxsiy chatlaridagi xabarlar tarixini o'qiy olasan va
   xabar yubora olasan (hisobot yig'ish, qidirish, statistikalar va h.k.).

B) Umumiy savol-javob: agar foydalanuvchi Telegram bilan bog'liq bo'lmagan savol bersa
   (ilmiy, umumiy bilim, maslahat, tarjima, hisob-kitob, kod yozish va h.k.) - hech qanday
   vosita (tool) chaqirmasdan, to'g'ridan-to'g'ri o'zing bilganingdan to'liq va aniq javob
   ber. Bunda hallucinate qilmaslik talabi (8-band) faqat Telegram ma'lumotlariga tegishli -
   umumiy bilim savollariga o'zingning bilimingdan erkin javob ber.

Qaysi turdagi vazifa ekanini xabar mazmunidan o'zing aniqlab ol va mosiga ko'ra harakat qil.

Telegram vazifalari uchun ishlash tartibi:
1. Foydalanuvchi senga erkin matnda topshiriq (TZ) beradi - bu har xil bo'lishi mumkin
   (hisobot yig'ish, xabarlarni qidirish, kimgadir xabar yuborish, statistikani hisoblash va h.k.).
2. Topshiriqni bajarish uchun kerakli vositalarni ketma-ket chaqir. Avval `list_dialogs` bilan
   kerakli chat/guruhni top (nom to'liq mos kelmasa ham, eng yaqinini tanla).
3. Sana oraliqlari bilan ishlaganda (masalan "shu oy", "o'tgan hafta") avval `get_current_datetime`
   orqali bugungi sanani bil, keyin oraliqni hisoblab `get_chat_history`ga ber.
4. Agar foydalanuvchi natijani biror chatga (masalan o'ziga, "Saved Messages"ga yoki guruhga)
   yuborishni so'rasa - `send_message` orqali yubor. "Saved Messages" - bu foydalanuvchining
   o'zi bilan bo'lgan chati, `chat="me"` orqali murojaat qilinadi.
5. Agar topshiriqda aniq qayerga yuborish aytilmagan bo'lsa - natijani shunchaki javob matni
   sifatida qaytar (bot foydalanuvchiga shu matnni yuboradi), alohida send_message shart emas.
6. Hisobot/xulosa tayyorlashda: ma'lumotlarni guruhlab, sanalar, mualliflar va asosiy
   ko'rsatkichlarni aniq ko'rsat. O'zbek tilida, tushunarli va tartibli formatda yoz.
7. Agar kerakli chat topilmasa yoki ma'lumot yetarli bo'lmasa - vositalarni qayta urinish
   o'rniga, foydalanuvchiga aniq nima yetishmayotganini tushuntirib ber.
8. Hech qachon o'zingdan ma'lumot o'ylab topma (hallucinate qilma) - faqat vositalardan
   olingan haqiqiy ma'lumotga tayan.

Sen to'liq avtonom ishlaysan - foydalanuvchidan qo'shimcha tasdiq so'ramasdan, topshiriqni
oxirigacha bajarib, natijani taqdim et.

Yakuniy javobni formatlash (Telegram'ga yuboriladi):
- Javob Telegram HTML formatida bo'lishi kerak. Faqat shu teglardan foydalan: <b>qalin</b>,
  <i>kursiv</i>, <u>tagiga chizilgan</u>, <code>kod/raqam</code>, <a href="...">link</a>.
  Boshqa hech qanday HTML teg ishlatma.
- Markdown belgilarini umuman ishlatma: #, ##, **, __, ``` , - (ro'yxat uchun), --- va
  shunga o'xshashlarni yozma. Ular Telegramda chiroyli ko'rinmaydi.
- Sarlavha/bo'lim nomi kerak bo'lsa <b>qalin matn</b> dan foydalan, # dan emas.
- Ro'yxat elementlari uchun "-" yoki "*" o'rniga "•" belgisidan foydalan.
- Ortiqcha heshteglar (#tag) qo'yma.
- Matnni bo'limlarga bo'lib, orasiga bo'sh qator qo'yib, o'qish oson bo'ladigan tarzda yoz.
- HTML maxsus belgilarini (<, >, &) faqat teg sifatida ishlat, oddiy matn ichida ularni
  yozma (kerak bo'lsa o'rniga so'z bilan ifodala).
"""

TOOLS = [
    {
        "name": "get_current_datetime",
        "description": "Hozirgi sana va vaqtni qaytaradi (Toshkent vaqti, UTC+5). Sana oraliqlarini hisoblashdan oldin shu vositani chaqir.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_dialogs",
        "description": "Foydalanuvchining barcha chatlari (guruh, kanal, shaxsiy) ro'yxatini qaytaradi. "
        "query berilsa, nomi yoki username'ida shu so'z bor chatlarni filtrlaydi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Chat nomidan qidiriladigan qism (ixtiyoriy)"},
                "limit": {"type": "integer", "description": "Qaytariladigan maksimal chat soni (default 50)"},
            },
        },
    },
    {
        "name": "get_chat_history",
        "description": "Berilgan chatdan xabarlar tarixini qaytaradi, ixtiyoriy ravishda sana oraliqi va kalit so'z bo'yicha filtrlaydi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat": {"type": "string", "description": "Chat nomi (to'liq yoki qisman), @username, chat ID yoki \"me\" (Saved Messages)"},
                "start_date": {"type": "string", "description": "Boshlanish sanasi YYYY-MM-DD formatida (ixtiyoriy)"},
                "end_date": {"type": "string", "description": "Tugash sanasi YYYY-MM-DD formatida, kiritilgan kun ham hisobga olinadi (ixtiyoriy)"},
                "limit": {"type": "integer", "description": "Maksimal xabar soni (default 200, max 1000)"},
                "keyword": {"type": "string", "description": "Faqat shu so'zni o'z ichiga olgan xabarlarni qaytarish (ixtiyoriy)"},
                "only_from_me": {"type": "boolean", "description": "Faqat foydalanuvchining o'zi yozgan xabarlarni qaytarish (default false)"},
            },
            "required": ["chat"],
        },
    },
    {
        "name": "search_messages",
        "description": "Berilgan chat ichida Telegramning ichki qidiruvi orqali kalit so'z bo'yicha xabarlarni qidiradi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat": {"type": "string", "description": "Chat nomi, @username, chat ID yoki \"me\""},
                "query": {"type": "string", "description": "Qidiriladigan matn"},
                "limit": {"type": "integer", "description": "Maksimal natija soni (default 50, max 200)"},
            },
            "required": ["chat", "query"],
        },
    },
    {
        "name": "send_message",
        "description": "Berilgan chatga matnli xabar yuboradi (foydalanuvchining shaxsiy akkounti nomidan). "
        "O'ziga/Saved Messages'ga yuborish uchun chat=\"me\" ishlatiladi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat": {"type": "string", "description": "Chat nomi, @username, chat ID yoki \"me\""},
                "text": {"type": "string", "description": "Yuboriladigan matn"},
            },
            "required": ["chat", "text"],
        },
    },
    {
        "name": "get_chat_info",
        "description": "Chat haqida umumiy ma'lumot (turi, ID, a'zolar soni) qaytaradi.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chat": {"type": "string", "description": "Chat nomi, @username yoki chat ID"},
            },
            "required": ["chat"],
        },
    },
]


class ClaudeAgent:
    def __init__(self, toolset: TelegramToolset):
        self.toolset = toolset
        self.client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    async def _dispatch_tool(self, name: str, tool_input: dict) -> dict:
        try:
            if name == "get_current_datetime":
                return self.toolset.get_current_datetime()
            if name == "list_dialogs":
                return {"dialogs": await self.toolset.list_dialogs(tool_input.get("query"), tool_input.get("limit", 50))}
            if name == "get_chat_history":
                return await self.toolset.get_chat_history(
                    chat=tool_input["chat"],
                    start_date=tool_input.get("start_date"),
                    end_date=tool_input.get("end_date"),
                    limit=tool_input.get("limit", 200),
                    keyword=tool_input.get("keyword"),
                    only_from_me=tool_input.get("only_from_me", False),
                )
            if name == "search_messages":
                return await self.toolset.search_messages(
                    chat=tool_input["chat"], query=tool_input["query"], limit=tool_input.get("limit", 50)
                )
            if name == "send_message":
                return await self.toolset.send_message(chat=tool_input["chat"], text=tool_input["text"])
            if name == "get_chat_info":
                return await self.toolset.get_chat_info(chat=tool_input["chat"])
            return {"error": f"Noma'lum vosita: {name}"}
        except Exception as exc:
            logger.exception("Tool error (%s): %s", name, exc)
            return {"error": str(exc)}

    async def run_task(self, task_text: str, history: list[dict] | None = None) -> str:
        # Bo'sh content li xabarlarni filter qilish (400 xatosini oldini oladi)
        clean_history = [m for m in (history or []) if m.get('content')]
        messages = clean_history + [{'role': 'user', 'content': task_text}]

        for step in range(config.MAX_AGENT_STEPS):
            response = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                return "".join(block.text for block in response.content if block.type == "text").strip() or "(bo'sh javob)"

            messages.append({"role": "assistant", "content": response.content})

            tool_blocks = [block for block in response.content if block.type == "tool_use"]
            if not tool_blocks:
                return ''.join(b.text for b in response.content if b.type == "text").strip() or "(bo'sh javob)"
            for block in tool_blocks:
                logger.info("Tool call step=%s name=%s input=%s", step, block.name, block.input)
            results = await asyncio.gather(
                *(self._dispatch_tool(block.name, block.input or {}) for block in tool_blocks)
            )
            tool_results = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str)[:20000],
                }
                for block, result in zip(tool_blocks, results)
            ]

            messages.append({"role": "user", "content": tool_results})

        return "Topshiriq juda murakkab bo'lib ketdi (qadamlar limiti tugadi). Iltimos, topshiriqni soddalashtirib qayta urinib ko'ring."
