from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["OPENAI_MODEL"] = "gpt-5.5"
os.environ["OPENAI_REASONING_EFFORT"] = "high"

from app.config import settings
from app.services.openai_service import OpenAIService


class Message:
    content = '{"ok": true}'


class Choice:
    message = Message()


class Response:
    choices = [Choice()]


class Completions:
    def __init__(self) -> None:
        self.kwargs = None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        return Response()


class Chat:
    def __init__(self) -> None:
        self.completions = Completions()


class FakeClient:
    def __init__(self) -> None:
        self.chat = Chat()


async def run_test() -> None:
    settings.openai_model = "gpt-5.5"
    settings.openai_reasoning_effort = "high"
    service = OpenAIService()
    service.client = FakeClient()
    await service.json_chat("system", "user", {})
    kwargs = service.client.chat.completions.kwargs
    assert "temperature" not in kwargs, "Reasoning modelga temperature yuborilmasligi kerak"
    assert kwargs.get("reasoning_effort") == "high"
    print("OPENAI PARAMETER GUARD PASSED: gpt-5.5 uchun temperature yuborilmaydi")


if __name__ == "__main__":
    asyncio.run(run_test())
