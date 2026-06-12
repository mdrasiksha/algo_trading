"""Runtime configuration helpers for the Zerodha options bot.

Secrets are intentionally loaded from environment variables or local ignored
files. Do not commit access tokens or API secrets to Git.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOKEN_PATH = PROJECT_ROOT / "access_token.txt"


@dataclass(frozen=True)
class Settings:
    """Validated bot settings loaded from environment variables."""

    api_key: str
    api_secret: str | None = None
    access_token: str | None = None
    access_token_path: Path = DEFAULT_TOKEN_PATH
    paper_trading: bool = True
    lots: int = 1
    max_daily_loss: float = 0.0
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def read_access_token(path: Path = DEFAULT_TOKEN_PATH) -> str | None:
    """Read an access token from an ignored local file if present."""

    if not path.exists():
        return None
    token = path.read_text(encoding="utf-8").strip()
    return token or None


def write_access_token(token: str, path: Path = DEFAULT_TOKEN_PATH) -> None:
    """Persist the daily access token with owner-only file permissions."""

    path.write_text(token.strip(), encoding="utf-8")
    try:
        path.chmod(0o600)
    except PermissionError:
        # Some filesystems do not support chmod; the file is still gitignored.
        pass


def load_settings(require_token: bool = True, require_secret: bool = False) -> Settings:
    """Load settings and fail fast for missing required credentials."""

    token_path = Path(os.getenv("KITE_ACCESS_TOKEN_PATH", str(DEFAULT_TOKEN_PATH)))
    api_key = os.getenv("KITE_API_KEY")
    api_secret = os.getenv("KITE_API_SECRET")
    access_token = os.getenv("KITE_ACCESS_TOKEN") or read_access_token(token_path)

    missing: list[str] = []
    if not api_key:
        missing.append("KITE_API_KEY")
    if require_secret and not api_secret:
        missing.append("KITE_API_SECRET")
    if require_token and not access_token:
        missing.append("KITE_ACCESS_TOKEN or access_token.txt")
    if missing:
        raise RuntimeError(
            "Missing required configuration: " + ", ".join(missing)
        )

    return Settings(
        api_key=api_key or "",
        api_secret=api_secret,
        access_token=access_token,
        access_token_path=token_path,
        paper_trading=_env_bool("PAPER_TRADING", True),
        lots=_env_int("LOTS", 1),
        max_daily_loss=_env_float("MAX_DAILY_LOSS", 0.0),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
    )
