"""Market-data helpers for index and option pricing."""

from __future__ import annotations

from kiteconnect import KiteConnect

from .kite_client import kite_retry


NIFTY_SPOT = "NSE:NIFTY 50"
SENSEX_SPOT = "BSE:SENSEX"


@kite_retry()
def get_last_price(kite: KiteConnect, instrument: str) -> float:
    """Return the last traded price for a Kite instrument key."""

    quote = kite.ltp(instrument)
    return float(quote[instrument]["last_price"])


def round_to_strike(price: float, step: int) -> int:
    """Round a spot price to its nearest option strike."""

    return int(round(price / step) * step)


def get_atm_strike(kite: KiteConnect, spot_instrument: str = NIFTY_SPOT, step: int = 50) -> tuple[float, int]:
    """Fetch spot LTP and compute the nearest ATM strike."""

    price = get_last_price(kite, spot_instrument)
    return price, round_to_strike(price, step)


@kite_retry()
def get_option_premiums(kite: KiteConnect, ce_symbol: str, pe_symbol: str) -> tuple[float, float]:
    """Fetch CE and PE premiums with one batched ltp call."""

    keys = [f"NFO:{ce_symbol}", f"NFO:{pe_symbol}"]
    quotes = kite.ltp(keys)
    return float(quotes[keys[0]]["last_price"]), float(quotes[keys[1]]["last_price"])
