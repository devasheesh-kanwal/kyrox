import os
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv

# .env file se keys load karo
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    # OpenTopography Config
    OPEN_TOPOGRAPHY_KEY = os.getenv("OPEN_TOPOGRAPHY_KEY")
    OPEN_TOPOGRAPHY_URL = os.getenv("OPEN_TOPOGRAPHY_URL")

    # Validation: Agar key nahi mili toh error do
    @staticmethod
    def validate():
        if not Config.OPEN_TOPOGRAPHY_KEY:
            raise ValueError("OPEN_TOPOGRAPHY_KEY missing in .env file!")
        if not Config.OPEN_TOPOGRAPHY_URL:
            raise ValueError("OPEN_TOPOGRAPHY_URL missing in .env file!")

        # Validate URL is well-formed and uses HTTPS, not just "truthy"
        parsed = urlparse(Config.OPEN_TOPOGRAPHY_URL)
        if parsed.scheme != "https":
            raise ValueError(
                "OPEN_TOPOGRAPHY_URL must use HTTPS (got: "
                f"{parsed.scheme or 'no scheme'})"
            )
        if not parsed.netloc:
            raise ValueError("OPEN_TOPOGRAPHY_URL is not a valid URL")

    @staticmethod
    def masked_key() -> str:
        """Safe-to-log representation of the key (for debugging/logs)."""
        key = Config.OPEN_TOPOGRAPHY_KEY
        if not key:
            return "<missing>"
        if len(key) <= 8:
            return "****"
        return f"{key[:4]}...{key[-4:]}"


# Fail fast at import time, not later when a request happens mid-flight
Config.validate()