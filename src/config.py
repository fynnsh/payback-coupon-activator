import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Optional settings with defaults
    SCHEDULE_INTERVAL_HOURS: int = int(os.getenv("SCHEDULE_INTERVAL_HOURS", "24"))
    COOLDOWN_SECONDS: int = int(os.getenv("COOLDOWN_SECONDS", "1"))
    HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"

    # Rate limit settings
    RATE_LIMIT_BATCH_SIZE: int = int(os.getenv("RATE_LIMIT_BATCH_SIZE", "100"))
    RATE_LIMIT_PAUSE_HOURS: float = float(os.getenv("RATE_LIMIT_PAUSE_HOURS", "1"))

    # Web UI
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8080"))

    # URLs
    COUPONS_URL: str = "https://www.payback.de/coupons"

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    COOKIES_FILE: Path = Path(os.getenv("COOKIES_FILE", str(BASE_DIR / "cookies.json")))
    LOGS_DIR: Path = BASE_DIR / "logs"
    SCREENSHOTS_DIR: Path = LOGS_DIR / "screenshots"

    # Timeouts (in milliseconds)
    DEFAULT_TIMEOUT: int = 30000
    NAVIGATION_TIMEOUT: int = 60000

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present.

        Missing cookies.json is a warning (can be uploaded via Web UI).
        """
        if not cls.COOKIES_FILE.exists():
            raise ValueError(f"Cookies file not found: {cls.COOKIES_FILE}")
        return True

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure required directories exist."""
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
