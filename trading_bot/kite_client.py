"""Kite Connect client factory and retry wrapper."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
import logging
import time
from typing import ParamSpec, TypeVar

from kiteconnect import KiteConnect
from kiteconnect.exceptions import NetworkException, TokenException

from .settings import Settings, load_settings


LOGGER = logging.getLogger(__name__)
P = ParamSpec("P")
R = TypeVar("R")


def create_kite(settings: Settings | None = None) -> KiteConnect:
    """Create an authenticated KiteConnect client from runtime settings."""

    settings = settings or load_settings(require_token=True)
    kite = KiteConnect(api_key=settings.api_key)
    if settings.access_token:
        kite.set_access_token(settings.access_token)
    return kite


def kite_retry(
    attempts: int = 3,
    base_delay_seconds: float = 0.5,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry transient Kite network failures without hiding token failures."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            last_error: NetworkException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except TokenException:
                    LOGGER.exception("Kite access token is invalid or expired")
                    raise
                except NetworkException as exc:
                    last_error = exc
                    if attempt == attempts:
                        break
                    sleep_for = base_delay_seconds * (2 ** (attempt - 1))
                    LOGGER.warning(
                        "Transient Kite network error in %s; retrying in %.1fs (%s/%s)",
                        func.__name__,
                        sleep_for,
                        attempt,
                        attempts,
                    )
                    time.sleep(sleep_for)
            raise last_error  # type: ignore[misc]

        return wrapper

    return decorator
