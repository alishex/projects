from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Iterable


class SecretMaskingFilter(logging.Filter):
    def __init__(self, secrets: Iterable[str] | None = None) -> None:
        super().__init__()
        self.secrets = [s for s in (secrets or []) if s and s not in {"replace_me", "telegram_bot_token_here"}]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self.secrets:
            message = message.replace(secret, "***")
        message = re.sub(r"(access_token=)[^&\s]+", r"\1***", message)
        record.msg = message
        record.args = ()
        return True


def setup_logging(level: str = "INFO", secrets: Iterable[str] | None = None) -> None:
    Path("logs").mkdir(exist_ok=True)
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    mask_filter = SecretMaskingFilter(secrets)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(mask_filter)

    app_file = RotatingFileHandler("logs/app.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    app_file.setFormatter(formatter)
    app_file.addFilter(mask_filter)

    err_file = RotatingFileHandler("logs/error.log", maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    err_file.setLevel(logging.ERROR)
    err_file.setFormatter(formatter)
    err_file.addFilter(mask_filter)

    root.addHandler(console)
    root.addHandler(app_file)
    root.addHandler(err_file)
