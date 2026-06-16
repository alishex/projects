from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _ids(value: str | None) -> list[int]:
    result: list[int] = []
    for part in (value or "").replace(";", ",").split(","):
        part = part.strip()
        if part and part.lstrip("-").isdigit():
            result.append(int(part))
    return result


@dataclass(slots=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")

    admin_ids: list[int] = None  # type: ignore[assignment]
    db_path: Path = BASE_DIR / os.getenv("DB_PATH", "data/database.db")
    export_dir: Path = BASE_DIR / os.getenv("EXPORT_DIR", "exports")
    log_file: Path = BASE_DIR / os.getenv("LOG_FILE", "logs/bot.log")
    default_shop_address: str = os.getenv("DEFAULT_SHOP_ADDRESS", "ALLMAX bosh ofisi")
    default_branch: str = os.getenv("DEFAULT_BRANCH", "ALLMAX")
    timezone: str = os.getenv("TIMEZONE", "Asia/Tashkent")
    regulations_dir: Path = BASE_DIR / os.getenv("REGULATIONS_DIR", "reglamentlar")
    start_image_path: Path = BASE_DIR / os.getenv("START_IMAGE_PATH", "allmax_hr_start.jpg")

    # Clockster API
    clockster_enabled: bool = os.getenv("CLOCKSTER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    clockster_api_base: str = os.getenv("CLOCKSTER_API_BASE", "https://api.clockster.com/company/v2/").strip()
    clockster_api_token: str = os.getenv("CLOCKSTER_API_TOKEN", "").strip()
    clockster_employees_endpoints: str = os.getenv("CLOCKSTER_EMPLOYEES_ENDPOINTS", "employees,people,users")
    clockster_attendance_endpoints: str = os.getenv("CLOCKSTER_ATTENDANCE_ENDPOINTS", "attendance,attendances,timesheets,checkins")
    clockster_sync_interval_minutes: int = int(os.getenv("CLOCKSTER_SYNC_INTERVAL_MINUTES", "15") or 15)
    clockster_lookback_days: int = int(os.getenv("CLOCKSTER_LOOKBACK_DAYS", "7") or 7)
    clockster_match_threshold: float = float(os.getenv("CLOCKSTER_MATCH_THRESHOLD", "0.78") or 0.78)

    def __post_init__(self) -> None:
        self.admin_ids = _ids(os.getenv("ADMIN_IDS"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.regulations_dir.mkdir(parents=True, exist_ok=True)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def clockster_ready(self) -> bool:
        return self.clockster_enabled and bool(self.clockster_api_token)

    @property
    def clockster_employee_paths(self) -> list[str]:
        return [p.strip().strip("/") for p in self.clockster_employees_endpoints.split(",") if p.strip()]

    @property
    def clockster_attendance_paths(self) -> list[str]:
        return [p.strip().strip("/") for p in self.clockster_attendance_endpoints.split(",") if p.strip()]


settings = Settings()
