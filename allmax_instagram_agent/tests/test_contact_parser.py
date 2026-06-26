from app.config import Settings
from app.services.openai_parser import ContactParser


def test_parser_name_phone():
    parser = ContactParser(Settings(openai_api_key="replace_me"))
    result = parser.parse("Salom, ismim Ali, raqamim 90 123 45 67")
    assert result.phone == "+998901234567"
    assert result.name == "Ali"


def test_parser_phone_only():
    parser = ContactParser(Settings(openai_api_key="replace_me"))
    result = parser.parse("+998 93 111 22 33")
    assert result.phone == "+998931112233"
