"""Centralised environment-backed configuration for Kite scripts.

Keep this file free of secrets. Put real values in `.env` (local only) or in
runtime environment variables such as GitHub Actions secrets / deployment
secret managers.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def require_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def optional_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """Return an optional environment variable."""
    return os.getenv(name) or default


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value else default


@dataclass(frozen=True)
class KiteSettings:
    api_key: str
    api_secret: Optional[str]
    access_token: Optional[str]
    paper_trading: bool
    default_lot_size: int
    max_daily_loss: float
    max_loss_per_trade: float
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]


# Backward-compatible names for older utility scripts. These now come from
# environment variables instead of hard-coded secrets.
API_KEY = require_env("KITE_API_KEY")
API_SECRET = optional_env("KITE_API_SECRET")
ACCESS_TOKEN = optional_env("KITE_ACCESS_TOKEN")


def load_kite_settings(require_token: bool = True) -> KiteSettings:
    access_token = optional_env("KITE_ACCESS_TOKEN")
    if require_token and not access_token:
        raise ValueError("Missing required environment variable: KITE_ACCESS_TOKEN")
    return KiteSettings(
        api_key=API_KEY,
        api_secret=API_SECRET,
        access_token=access_token,
        paper_trading=env_bool("PAPER_TRADING", default=True),
        default_lot_size=env_int("DEFAULT_LOT_SIZE", 50),
        max_daily_loss=env_float("MAX_DAILY_LOSS", 8000.0),
        max_loss_per_trade=env_float("MAX_LOSS_PER_TRADE", 3000.0),
        telegram_bot_token=optional_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=optional_env("TELEGRAM_CHAT_ID"),
    )
