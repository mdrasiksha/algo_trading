import datetime as dt
import logging
import math
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from kiteconnect import KiteConnect

load_dotenv()


@dataclass(frozen=True)
class Config:
    api_key: str
    access_token: str
    telegram_token: Optional[str]
    telegram_chat_id: Optional[str]
    symbol: str = "NIFTY 50"
    exchange: str = "NSE"
    derivatives_exchange: str = "NFO"
    lot_size: int = 50
    max_trades: int = 3
    max_daily_loss: float = 8000.0
    max_losses: int = 2
    max_loss_per_trade: float = 3000.0
    sl_pct: float = 0.30
    target_pct: float = 0.50
    proximity_tol: float = 0.001
    range_pct: float = 0.007
    entry_start: dt.time = dt.time(9, 45)
    entry_end: dt.time = dt.time(13, 0)
    force_exit: dt.time = dt.time(15, 10)
    strike_step: int = 50
    hedge_dist: int = 150
    sell_dist: int = 100
    poll_interval_sec: int = 5
    order_timeout_sec: int = 20
    order_retry: int = 3
    api_retry: int = 3
    cooldown_seconds: int = 300


@dataclass
class Position:
    spread_type: str
    sell_symbol: str
    buy_symbol: str
    qty: int
    sell_entry: float
    buy_entry: float
    entered_at: dt.datetime = field(default_factory=dt.datetime.now)


@dataclass
class RuntimeState:
    trades: int = 0
    daily_pnl: float = 0.0
    loss_count: int = 0
    position: Optional[Position] = None
    kill_switch: bool = False
    last_entry_ts: Optional[dt.datetime] = None
    last_telegram_message: Optional[str] = None


class TradingBot:
    def __init__(self, config: Config):
        self.config = config
        self.state = RuntimeState()
        self.kite = KiteConnect(api_key=config.api_key)
        self.kite.set_access_token(config.access_token)
        self.logger = logging.getLogger("trading_bot")
        self.instrument_index: Dict[Tuple[dt.date, int, str], str] = {}
        self.current_expiry: Optional[dt.date] = None

    def _api_call(self, fn, *args, **kwargs):
        backoff = 1.0
        for attempt in range(1, self.config.api_retry + 1):
            try:
                return fn(*args, **kwargs)
            except Exception:
                self.logger.exception("API call failed on attempt %s", attempt)
                if attempt == self.config.api_retry:
                    raise
                time.sleep(backoff)
                backoff *= 2

    def _telegram(self, msg: str) -> None:
        if not self.config.telegram_token or not self.config.telegram_chat_id:
            return
        if msg == self.state.last_telegram_message:
            return
        try:
            url = f"https://api.telegram.org/bot{self.config.telegram_token}/sendMessage"
            requests.post(url, data={"chat_id": self.config.telegram_chat_id, "text": msg}, timeout=5)
            self.state.last_telegram_message = msg
        except Exception:
            self.logger.exception("Telegram send failed")

    @staticmethod
    def _round_to_step(price: float, step: int) -> int:
        return int(round(price / step) * step)

    def _ltp(self, symbol: str) -> float:
        quote = self._api_call(self.kite.ltp, symbol)
        return list(quote.values())[0]["last_price"]

    def _get_spot(self) -> float:
        symbol = f"{self.config.exchange}:{self.config.symbol}"
        return self._ltp(symbol)

    def _historical(self, from_dt: dt.datetime, to_dt: dt.datetime, interval: str):
        return self._api_call(
            self.kite.historical_data,
            instrument_token=256265,
            from_date=from_dt,
            to_date=to_dt,
            interval=interval,
        )

    def _prev_day_hl(self) -> Tuple[float, float]:
        to_date = dt.date.today() - dt.timedelta(days=1)
        from_date = to_date - dt.timedelta(days=7)
        data = self._historical(
            dt.datetime.combine(from_date, dt.time(0, 0)),
            dt.datetime.combine(to_date, dt.time(23, 59)),
            "day",
        )
        if not data:
            raise RuntimeError("No previous day candles found")
        yesterday = data[-1]
        return float(yesterday["high"]), float(yesterday["low"])

    def _first_15m_hl(self) -> Tuple[float, float]:
        today = dt.date.today()
        data = self._historical(
            dt.datetime.combine(today, dt.time(9, 15)),
            dt.datetime.combine(today, dt.time(9, 30)),
            "5minute",
        )
        if not data:
            raise RuntimeError("No first 15m candles found")
        highs = [c["high"] for c in data]
        lows = [c["low"] for c in data]
        return float(max(highs)), float(min(lows))

    def _last_candle(self) -> Dict[str, float]:
        today = dt.date.today()
        data = self._historical(
            dt.datetime.combine(today, dt.time(9, 15)),
            dt.datetime.now(),
            "5minute",
        )
        if not data:
            raise RuntimeError("No intraday candles available")
        row = data[-1]
        return {"o": row["open"], "h": row["high"], "l": row["low"], "c": row["close"]}

    def _is_range_day(self, day_high: float, day_low: float, spot: float) -> bool:
        return ((day_high - day_low) / spot) < self.config.range_pct

    def _near(self, price: float, level: float) -> bool:
        return abs(price - level) / level < self.config.proximity_tol

    @staticmethod
    def _bullish_rejection(candle: Dict[str, float]) -> bool:
        body = abs(candle["c"] - candle["o"])
        lower_wick = min(candle["o"], candle["c"]) - candle["l"]
        return lower_wick > body * 1.5 and candle["c"] > candle["o"]

    @staticmethod
    def _bearish_rejection(candle: Dict[str, float]) -> bool:
        body = abs(candle["c"] - candle["o"])
        upper_wick = candle["h"] - max(candle["o"], candle["c"])
        return upper_wick > body * 1.5 and candle["c"] < candle["o"]

    def _compute_levels(self) -> Tuple[float, float]:
        pdh, pdl = self._prev_day_hl()
        f15h, f15l = self._first_15m_hl()
        resistance = max(pdh, f15h)
        support = min(pdl, f15l)
        return support, resistance

    def _pick_strikes(self, spot: float) -> Tuple[int, int, int, int]:
        atm = self._round_to_step(spot, self.config.strike_step)
        ce_sell = atm + self.config.sell_dist
        pe_sell = atm - self.config.sell_dist
        ce_buy = ce_sell + self.config.hedge_dist
        pe_buy = pe_sell - self.config.hedge_dist
        return ce_sell, ce_buy, pe_sell, pe_buy

    def _build_instrument_index(self) -> None:
        instruments = self._api_call(self.kite.instruments, self.config.derivatives_exchange)
        expiries: List[dt.date] = []
        for inst in instruments:
            if inst.get("name") != "NIFTY" or inst.get("segment") != "NFO-OPT":
                continue
            expiry = inst.get("expiry")
            if expiry and expiry >= dt.date.today():
                expiries.append(expiry)

        if not expiries:
            raise RuntimeError("No valid NIFTY option expiries found")

        nearest_expiry = min(expiries)
        self.current_expiry = nearest_expiry
        self.instrument_index.clear()

        for inst in instruments:
            if (
                inst.get("name") == "NIFTY"
                and inst.get("segment") == "NFO-OPT"
                and inst.get("expiry") == nearest_expiry
            ):
                strike = int(round(float(inst.get("strike", 0))))
                opt_type = inst.get("instrument_type")
                if opt_type in {"CE", "PE"}:
                    self.instrument_index[(nearest_expiry, strike, opt_type)] = inst["tradingsymbol"]

        if not self.instrument_index:
            raise RuntimeError("Failed to build instrument index for nearest expiry")

    def _option_symbol(self, strike: int, opt_type: str) -> str:
        if not self.current_expiry or not self.instrument_index:
            self._build_instrument_index()

        assert self.current_expiry is not None
        key = (self.current_expiry, strike, opt_type)
        symbol = self.instrument_index.get(key)
        if symbol:
            return symbol

        self._build_instrument_index()
        key = (self.current_expiry, strike, opt_type)
        symbol = self.instrument_index.get(key)
        if not symbol:
            raise RuntimeError(
                f"Option symbol not found for strike={strike}, type={opt_type}, expiry={self.current_expiry}"
            )
        return symbol

    def _place_market_order(self, symbol: str, qty: int, side: str) -> float:
        for attempt in range(1, self.config.order_retry + 1):
            try:
                order_id = self._api_call(
                    self.kite.place_order,
                    variety=self.kite.VARIETY_REGULAR,
                    exchange=self.config.derivatives_exchange,
                    tradingsymbol=symbol,
                    transaction_type=side,
                    quantity=qty,
                    product=self.kite.PRODUCT_MIS,
                    order_type=self.kite.ORDER_TYPE_MARKET,
                )
                return self._wait_for_order_fill(order_id)
            except Exception:
                self.logger.exception("Order %s %s failed attempt %s", side, symbol, attempt)
                if attempt == self.config.order_retry:
                    raise
                time.sleep(1.5 * attempt)
        raise RuntimeError("Unexpected order placement state")

    def _wait_for_order_fill(self, order_id: str) -> float:
        deadline = time.time() + self.config.order_timeout_sec
        while time.time() < deadline:
            orders = self._api_call(self.kite.orders)
            order = next((o for o in orders if o.get("order_id") == order_id), None)
            if not order:
                time.sleep(1)
                continue

            status = order.get("status")
            filled = int(order.get("filled_quantity") or 0)
            qty = int(order.get("quantity") or 0)
            if status == "COMPLETE" and filled == qty:
                avg_price = float(order.get("average_price") or 0)
                if avg_price <= 0:
                    raise RuntimeError(f"Invalid average price for order {order_id}")
                return avg_price
            if status in {"CANCELLED", "REJECTED"}:
                raise RuntimeError(f"Order {order_id} {status}: {order.get('status_message')}")
            time.sleep(1)

        raise TimeoutError(f"Order {order_id} not fully filled in time")

    def _estimate_open_pnl(self, position: Position) -> float:
        sell_ltp = self._ltp(f"{self.config.derivatives_exchange}:{position.sell_symbol}")
        buy_ltp = self._ltp(f"{self.config.derivatives_exchange}:{position.buy_symbol}")
        sold_pnl = (position.sell_entry - sell_ltp) * position.qty
        hedge_pnl = (buy_ltp - position.buy_entry) * position.qty
        return sold_pnl + hedge_pnl

    def _close_position_and_get_realized_pnl(self, pos: Position) -> float:
        buyback_sell_leg = self._place_market_order(pos.sell_symbol, pos.qty, "BUY")
        squareoff_buy_leg = self._place_market_order(pos.buy_symbol, pos.qty, "SELL")
        sold_leg_pnl = (pos.sell_entry - buyback_sell_leg) * pos.qty
        hedge_leg_pnl = (squareoff_buy_leg - pos.buy_entry) * pos.qty
        return sold_leg_pnl + hedge_leg_pnl

    def _enter_spread(self, spread_kind: str, spot: float) -> None:
        now = dt.datetime.now()
        if self.state.last_entry_ts and (now - self.state.last_entry_ts).total_seconds() < self.config.cooldown_seconds:
            return

        ce_sell, ce_buy, pe_sell, pe_buy = self._pick_strikes(spot)
        if spread_kind == "CE":
            sell_symbol = self._option_symbol(ce_sell, "CE")
            buy_symbol = self._option_symbol(ce_buy, "CE")
        else:
            sell_symbol = self._option_symbol(pe_sell, "PE")
            buy_symbol = self._option_symbol(pe_buy, "PE")

        buy_entry = self._place_market_order(buy_symbol, self.config.lot_size, "BUY")
        sell_entry = self._place_market_order(sell_symbol, self.config.lot_size, "SELL")

        position = Position(
            spread_type=spread_kind,
            sell_symbol=sell_symbol,
            buy_symbol=buy_symbol,
            qty=self.config.lot_size,
            sell_entry=sell_entry,
            buy_entry=buy_entry,
        )

        max_risk_rupees = max(0.0, (position.sell_entry - position.buy_entry) * position.qty)
        if max_risk_rupees > self.config.max_loss_per_trade:
            realized_pnl = self._close_position_and_get_realized_pnl(position)
            self.state.daily_pnl += realized_pnl
            if realized_pnl < 0:
                self.state.loss_count += 1
            self._telegram(
                f"Entry reverted: theoretical risk {max_risk_rupees:.0f} > {self.config.max_loss_per_trade:.0f}, "
                f"realized pnl={realized_pnl:.0f}"
            )
            return

        self.state.position = position
        self.state.trades += 1
        self.state.last_entry_ts = now
        self._telegram(f"ENTRY {spread_kind} spread: SELL {sell_symbol} @ {sell_entry:.2f} / BUY {buy_symbol} @ {buy_entry:.2f}")

    def _exit_position(self, reason: str) -> None:
        pos = self.state.position
        if not pos:
            return

        try:
            realized_pnl = self._close_position_and_get_realized_pnl(pos)
        except Exception:
            self.logger.exception("Exit orders failed")
            self._telegram(f"CRITICAL: exit failed for {pos.sell_symbol}/{pos.buy_symbol}. Manual intervention required")
            self.state.kill_switch = True
            return

        self.state.daily_pnl += realized_pnl
        if realized_pnl < 0:
            self.state.loss_count += 1

        self._telegram(f"EXIT {reason}: pnl={realized_pnl:.0f}, day_pnl={self.state.daily_pnl:.0f}")
        self.state.position = None

    def _manage_trade(self) -> None:
        pos = self.state.position
        if not pos:
            return

        spread_pnl = self._estimate_open_pnl(pos)
        if spread_pnl <= -self.config.max_loss_per_trade:
            self._exit_position("hard_sl")
            return
        if spread_pnl >= self.config.max_loss_per_trade * 0.8:
            self._exit_position("target")
            return

        sell_cur = self._ltp(f"{self.config.derivatives_exchange}:{pos.sell_symbol}")
        if sell_cur >= pos.sell_entry * (1 + self.config.sl_pct):
            self._exit_position("sell_leg_sl")
        elif sell_cur <= pos.sell_entry * (1 - self.config.target_pct):
            self._exit_position("sell_leg_target")

    def _risk_limits_hit(self) -> bool:
        return (
            self.state.trades >= self.config.max_trades
            or self.state.loss_count >= self.config.max_losses
            or self.state.daily_pnl <= -self.config.max_daily_loss
        )

    def _validate_session(self) -> None:
        self._api_call(self.kite.profile)

    def run(self) -> None:
        self._validate_session()
        self._build_instrument_index()
        self._telegram("Bot started")
        support, resistance = self._compute_levels()
        self.logger.info("Computed levels support=%s resistance=%s", support, resistance)

        while True:
            now = dt.datetime.now().time()
            if self.state.kill_switch:
                self._telegram("Kill switch active, stopping bot")
                break

            if now >= self.config.force_exit:
                self._exit_position("force_exit")
                self._telegram("Market close workflow completed")
                break

            if self._risk_limits_hit():
                self._telegram("Risk limits hit, no new entries")
                self._exit_position("risk_limit")
                break

            if not (self.config.entry_start <= now <= self.config.entry_end):
                time.sleep(self.config.poll_interval_sec)
                continue

            try:
                spot = self._get_spot()
                day_high = max(spot, resistance)
                day_low = min(spot, support)

                if not self._is_range_day(day_high, day_low, spot):
                    time.sleep(self.config.poll_interval_sec)
                    continue

                if not self.state.position:
                    candle = self._last_candle()
                    if self._near(spot, support) and self._bullish_rejection(candle):
                        self._enter_spread("PE", spot)
                    elif self._near(spot, resistance) and self._bearish_rejection(candle):
                        self._enter_spread("CE", spot)
                else:
                    self._manage_trade()
            except Exception:
                self.logger.exception("Main loop error")
                self._telegram("Error in main loop. Retrying.")
                time.sleep(max(5, self.config.poll_interval_sec))
                continue

            time.sleep(self.config.poll_interval_sec)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required env variable: {name}")
    return value


def _optional_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value if value else None


def _setup_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _install_signal_handlers(bot: TradingBot) -> None:
    def _stop(*_) -> None:
        logging.getLogger("trading_bot").warning("Signal received, shutting down")
        bot.state.kill_switch = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)


if __name__ == "__main__":
    _setup_logging()
    cfg = Config(
        api_key=_require_env("KITE_API_KEY"),
        access_token=_require_env("KITE_ACCESS_TOKEN"),
        telegram_token=_optional_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_optional_env("TELEGRAM_CHAT_ID"),
    )
    trading_bot = TradingBot(cfg)
    _install_signal_handlers(trading_bot)
    trading_bot.run()
