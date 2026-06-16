from __future__ import annotations

import hashlib
import hmac
import logging

log = logging.getLogger(__name__)


def verify_meta_signature(raw_body: bytes, signature_header: str | None, app_secret: str | None) -> bool:
    if not app_secret or app_secret == "replace_me":
        log.warning("META_APP_SECRET is not configured; signature verification is bypassed for local/test mode.")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        log.warning("Missing or invalid X-Hub-Signature-256 header")
        return False
    expected = "sha256=" + hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    ok = hmac.compare_digest(expected, signature_header)
    log.info("Meta signature verification result: %s", ok)
    return ok
