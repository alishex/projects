from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .config import settings


def setup_logging() -> None:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    root = logging.getLogger()
    root.setLevel(settings.log_level)

    # Avoid duplicate handlers when uvicorn reloads.
    if root.handlers:
        return

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(log_format))
    console.setLevel(settings.log_level)

    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.setLevel(settings.log_level)

    root.addHandler(console)
    root.addHandler(file_handler)
