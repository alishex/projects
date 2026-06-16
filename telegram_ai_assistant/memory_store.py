import json
import os
import threading

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "conversation_history.json")
MAX_TURNS = 20  # har bir chat uchun saqlanadigan oxirgi savol-javob juftliklari soni

_lock = threading.Lock()


def _load_all() -> dict:
    if not os.path.exists(HISTORY_PATH):
        return {}
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_all(data: dict) -> None:
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_history(chat_id: int) -> list[dict]:
    with _lock:
        data = _load_all()
        return data.get(str(chat_id), [])


def append_turn(chat_id: int, user_text: str, assistant_text: str) -> None:
    with _lock:
        data = _load_all()
        key = str(chat_id)
        history = data.get(key, [])
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": assistant_text})
        data[key] = history[-MAX_TURNS * 2 :]
        _save_all(data)


def clear_history(chat_id: int) -> None:
    with _lock:
        data = _load_all()
        data.pop(str(chat_id), None)
        _save_all(data)
