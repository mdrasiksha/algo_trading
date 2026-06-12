"""Instrument lookup utilities for NFO options."""

from __future__ import annotations

from datetime import date
from typing import Any

from kiteconnect import KiteConnect

from .kite_client import kite_retry


Instrument = dict[str, Any]


@kite_retry()
def get_nfo_instruments(kite: KiteConnect) -> list[Instrument]:
    """Fetch NFO instrument master from Kite."""

    return list(kite.instruments("NFO"))


def find_options_by_strike(
    instruments: list[Instrument],
    underlying: str,
    strike: int,
    min_expiry: date | None = None,
) -> tuple[Instrument, Instrument]:
    """Find nearest-expiry CE and PE contracts for a strike."""

    candidates = [
        ins
        for ins in instruments
        if ins.get("name") == underlying
        and int(float(ins.get("strike", 0))) == int(strike)
        and ins.get("instrument_type") in {"CE", "PE"}
        and (min_expiry is None or ins.get("expiry") >= min_expiry)
    ]
    if not candidates:
        raise LookupError(f"No {underlying} options found for strike {strike}")

    nearest_expiry = min(ins["expiry"] for ins in candidates)
    by_type = {
        ins["instrument_type"]: ins
        for ins in candidates
        if ins.get("expiry") == nearest_expiry
    }
    if "CE" not in by_type or "PE" not in by_type:
        raise LookupError(
            f"Could not find both CE and PE for {underlying} {strike} {nearest_expiry}"
        )
    return by_type["CE"], by_type["PE"]


def lot_size_for_symbol(instruments: list[Instrument], symbol: str) -> int:
    """Return lot size for a tradingsymbol."""

    for ins in instruments:
        if ins.get("tradingsymbol") == symbol:
            return int(ins["lot_size"])
    raise LookupError(f"Instrument not found: {symbol}")
