"""Reusable Kite Connect helpers shared by small diagnostic scripts.

This module intentionally contains no strategy logic. It centralises client
creation, token loading, ATM rounding, NIFTY option lookup, and simple premium
reads so utility scripts do not duplicate authentication and instrument code.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, Optional

from kiteconnect import KiteConnect

from config import ACCESS_TOKEN, API_KEY, load_kite_settings


@dataclass(frozen=True)
class OptionPair:
    expiry: dt.date
    strike: int
    ce_symbol: str
    pe_symbol: str


def get_kite_client(require_token: bool = True) -> KiteConnect:
    """Create an authenticated KiteConnect client from environment settings."""
    settings = load_kite_settings(require_token=require_token)
    kite = KiteConnect(api_key=settings.api_key)
    if settings.access_token:
        kite.set_access_token(settings.access_token)
    return kite


def get_legacy_kite_client() -> KiteConnect:
    """Compatibility wrapper for older scripts that imported API_KEY directly."""
    kite = KiteConnect(api_key=API_KEY)
    if not ACCESS_TOKEN:
        raise ValueError("Missing required environment variable: KITE_ACCESS_TOKEN")
    kite.set_access_token(ACCESS_TOKEN)
    return kite


def round_to_step(price: float, step: int) -> int:
    return int(round(price / step) * step)


def get_ltp(kite: KiteConnect, instrument: str) -> float:
    quote = kite.ltp(instrument)
    if instrument not in quote:
        raise RuntimeError(f"LTP response missing instrument: {instrument}")
    return float(quote[instrument]["last_price"])


def get_nifty_spot(kite: KiteConnect) -> float:
    return get_ltp(kite, "NSE:NIFTY 50")


def get_atm_strike(spot: float, step: int = 50) -> int:
    return round_to_step(spot, step)


def find_nearest_option_pair(
    instruments: Iterable[dict],
    strike: int,
    name: str = "NIFTY",
    today: Optional[dt.date] = None,
) -> OptionPair:
    """Find nearest non-expired CE/PE symbols for a strike from NFO instruments."""
    today = today or dt.date.today()
    matches = [
        inst
        for inst in instruments
        if inst.get("name") == name
        and int(round(float(inst.get("strike", 0)))) == strike
        and inst.get("instrument_type") in {"CE", "PE"}
        and inst.get("expiry")
        and inst.get("expiry") >= today
    ]
    if not matches:
        raise RuntimeError(f"No {name} options found for strike {strike}")

    nearest_expiry = min(inst["expiry"] for inst in matches)
    symbols = {inst["instrument_type"]: inst["tradingsymbol"] for inst in matches if inst["expiry"] == nearest_expiry}
    if "CE" not in symbols or "PE" not in symbols:
        raise RuntimeError(f"Incomplete CE/PE pair for {name} {strike} {nearest_expiry}")
    return OptionPair(expiry=nearest_expiry, strike=strike, ce_symbol=symbols["CE"], pe_symbol=symbols["PE"])


def get_option_pair_for_atm(kite: KiteConnect, spot: Optional[float] = None) -> OptionPair:
    spot = spot if spot is not None else get_nifty_spot(kite)
    atm = get_atm_strike(spot)
    return find_nearest_option_pair(kite.instruments("NFO"), atm)
