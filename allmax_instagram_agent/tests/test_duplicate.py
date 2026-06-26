from app.config import Settings
from app.database import Database
from app.services.bitrix_service import BitrixService
from app.services.duplicate_service import DuplicateService


def test_local_duplicate(tmp_path):
    db = Database(str(tmp_path / "test.sqlite3"))
    db.init()
    db.add_sent_lead("+998901234567", "123", "1", "2")
    settings = Settings(bitrix_enable=False, bitrix_duplicate_check_enable=False)
    service = DuplicateService(settings, db, BitrixService(settings))
    result = service.check("+998901234567", "123")
    assert result.duplicate is True
    assert result.reason == "local_sqlite"
