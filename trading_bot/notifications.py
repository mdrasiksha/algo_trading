"""Notification helpers for operational alerts."""

from __future__ import annotations

import logging

import requests


LOGGER = logging.getLogger(__name__)


class TelegramNotifier:
    """Small Telegram sender with fail-open logging for bot alerts."""

    def __init__(self, bot_token: str | None, chat_id: str | None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, message: str) -> None:
        if not self.enabled:
            LOGGER.info("Telegram disabled: %s", message)
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        response = requests.post(
            url,
            json={"chat_id": self.chat_id, "text": message},
            timeout=10,
        )
        response.raise_for_status()
