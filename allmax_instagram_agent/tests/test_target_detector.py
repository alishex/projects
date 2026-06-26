from app.config import Settings
from app.services.target_detector import detect_target


def test_target_keyword_detection():
    payload = {"entry": [{"messaging": [{"message": {"text": "target reklama orqali yozdim"}}]}]}
    result = detect_target(payload, Settings())
    assert result.detected is True


def test_target_ad_id_detection():
    payload = {"entry": [{"messaging": [{"referral": {"ad_id": "123", "ad_title": "Kurtka ads"}}]}]}
    result = detect_target(payload, Settings())
    assert result.detected is True
    assert result.name == "Kurtka ads"
