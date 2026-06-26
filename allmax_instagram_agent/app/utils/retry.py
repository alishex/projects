from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")
log = logging.getLogger(__name__)


def retry_call(fn: Callable[[], T], attempts: int = 3, delay: float = 0.5, name: str = "operation") -> T:
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - production wrapper logs and retries.
            last_exc = exc
            log.warning("%s failed on attempt %s/%s: %s", name, attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(delay * attempt)
    assert last_exc is not None
    raise last_exc
