import httpx

from app.config import EXPO_PUSH_URL


def send_push(tokens: list[str], title: str, body: str) -> None:
    if not tokens:
        return
    messages = [{"to": token, "title": title, "body": body, "sound": "default"} for token in tokens]
    with httpx.Client(timeout=10) as client:
        client.post(EXPO_PUSH_URL, json=messages)
