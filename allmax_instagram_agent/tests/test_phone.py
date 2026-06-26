from app.utils.phone import extract_phone, format_phone_local, normalize_phone


def test_normalize_uz_formats():
    assert normalize_phone("+998 90 123 45 67") == "+998901234567"
    assert normalize_phone("998901234567") == "+998901234567"
    assert normalize_phone("90-123-45-67") == "+998901234567"
    assert normalize_phone("90.123.45.67") == "+998901234567"


def test_extract_phone_from_text():
    assert extract_phone("Salom ismim Ali raqamim 90 123 45 67") == "+998901234567"


def test_format_local():
    assert format_phone_local("+998901234567") == "90 123 45 67"
