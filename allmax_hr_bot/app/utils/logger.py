from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from app.config import settings


def setup_logging() -> None:
    settings.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            RotatingFileHandler(settings.log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
