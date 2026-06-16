"""
Telegram group chat_id aniqlash yordamchi skripti.

Ishlatish:
1) Botni guruhga qo'shing.
2) Guruhga biror xabar yozing.
3) .env ichida TELEGRAM_BOT_TOKEN to'ldiring.
4) python scripts/get_chat_id.py
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
import httpx

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN .env ichida yo'q")

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
response = httpx.get(url, timeout=20)
response.raise_for_status()
data = response.json()

print("Telegram getUpdates natijasi:\n")
for item in data.get("result", []):
    message = item.get("message") or item.get("channel_post") or {}
    chat = message.get("chat", {})
    user = message.get("from", {})
    if chat:
        print("CHAT:", chat.get("title") or chat.get("username") or chat.get("first_name"), "=>", chat.get("id"))
    if user:
        print("USER:", user.get("first_name"), user.get("username"), "=>", user.get("id"))
    print("-" * 50)
