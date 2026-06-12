"""Order placement abstractions with paper-trading support."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Protocol
from uuid import uuid4

from kiteconnect import KiteConnect

from .kite_client import kite_retry


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    quantity: int
    transaction_type: str
    product: str = "MIS"
    order_type: str = "MARKET"
    exchange: str = "NFO"


class Broker(Protocol):
    def place_order(self, request: OrderRequest) -> str:
        """Place an order and return an order id."""


class PaperBroker:
    """In-memory broker used for dry runs and SDET-safe tests."""

    def place_order(self, request: OrderRequest) -> str:
        order_id = f"paper-{uuid4()}"
        LOGGER.info("PAPER %s %s x %s -> %s", request.transaction_type, request.symbol, request.quantity, order_id)
        return order_id


class KiteBroker:
    """Thin live-order wrapper around KiteConnect."""

    def __init__(self, kite: KiteConnect) -> None:
        self.kite = kite

    @kite_retry(attempts=2)
    def place_order(self, request: OrderRequest) -> str:
        LOGGER.warning(
            "LIVE %s order requested for %s x %s",
            request.transaction_type,
            request.symbol,
            request.quantity,
        )
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=request.exchange,
            tradingsymbol=request.symbol,
            transaction_type=request.transaction_type,
            quantity=request.quantity,
            product=request.product,
            order_type=request.order_type,
        )
