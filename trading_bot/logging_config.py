"""Logging setup used by command-line scripts and bot runners."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_dir: str | Path = "logs", level: int = logging.INFO) -> None:
    """Configure console and rotating file logging once."""

    root = logging.getLogger()
    if root.handlers:
        return

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        Path(log_dir) / "bot.log", maxBytes=2_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)

    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)
