import os, time, math, json, requests, datetime as dt
import numpy as np
import pandas as pd
from kiteconnect import KiteConnect, KiteTicker
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KITE_API_KEY")
ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ---------- CONFIG ----------
SYMBOL = "NIFTY 50"
EXCHANGE = "NSE"
NFO = "NFO"

LOT_SIZE = 50
MAX_TRADES = 3
MAX_LOSS_PER_TRADE = 3000
DAILY_MAX_LOSS = 8000

SL_PCT = 0.30
TARGET_PCT = 0.50
TOL = 0.001  # 0.1%
RANGE_PCT = 0.007  # 0.7%

ENTRY_START = dt.time(9, 45)
ENTRY_END   = dt.time(13, 0)
FORCE_EXIT  = dt.time(15, 10)

STRIKE_STEP = 50
HEDGE_DIST  = 150   # points away
SELL_DIST   = 100   # OTM distance from spot

# ---------- STATE ----------
state = {
    "trades": 0,
    "daily_pnl": 0.0,
    "loss_count": 0,
    "positions": {},  # key: leg name -> dict
    "in_trade": False,
    "kill": False
}

# ---------- TELEGRAM ----------
def tg(msg):
    try:
        url = f"https://api.telegram.org/bot8616858927:AAH80IUB4auDygLznoioB_MkA1eeB6JsoCk/sendMessage"
        requests.post(url, data={"chat_id": TG_CHAT, "text": msg})
    except:
        pass

# ---------- HELPERS ----------
def round_to_step(x, step=50):
    return int(round(x / step) * step)

def ltp(symbol):
    q = kite.ltp(symbol)
    return list(q.values())[0]["last_price"]

def get_spot():
    return kite.ltp("NSE:NIFTY 50")["NSE:NIFTY 50"]["last_price"]

def prev_day_hl():
    to_date = dt.date.today() - dt.timedelta(days=1)
    from_date = to_date - dt.timedelta(days=5)
    data = kite.historical_data(
        instrument_token=256265,  # NIFTY 50 index token
        from_date=from_date,
        to_date=to_date,
        interval="day"
    )
    df = pd.DataFrame(data)
    y = df.iloc[-1]
    return float(y["high"]), float(y["low"])

def first_15m_hl():
    today = dt.date.today()
    data = kite.historical_data(
        instrument_token=256265,
        from_date=dt.datetime.combine(today, dt.time(9,15)),
        to_date=dt.datetime.combine(today, dt.time(9,30)),
        interval="5minute"
    )
    df = pd.DataFrame(data)
    return float(df["high"].max()), float(df["low"].min())

def is_range_day(day_high, day_low, spot):
    return (day_high - day_low) / spot < RANGE_PCT

def near(price, level):
    return abs(price - level) / level < TOL

def bullish_rejection(candle):
    # candle: dict with o,h,l,c
    body = abs(candle["c"] - candle["o"])
    lower_wick = min(candle["o"], candle["c"]) - candle["l"]
    return lower_wick > body * 1.5 and candle["c"] > candle["o"]

def bearish_rejection(candle):
    body = abs(candle["c"] - candle["o"])
    upper_wick = candle["h"] - max(candle["o"], candle["c"])
    return upper_wick > body * 1.5 and candle["c"] < candle["o"]

def last_candle():
    today = dt.date.today()
    data = kite.historical_data(
        instrument_token=256265,
        from_date=dt.datetime.combine(today, dt.time(9,15)),
        to_date=dt.datetime.now(),
        interval="5minute"
    )
    df = pd.DataFrame(data)
    row = df.iloc[-1]
    return {"o":row["open"],"h":row["high"],"l":row["low"],"c":row["close"]}

def option_symbol(strike, opt_type):
    # You can refine expiry lookup; using nearest weekly (example placeholder)
    # e.g., NIFTY24APR22500CE
    # Build using instrument dump in production
    today = dt.date.today()
    # Dummy: replace with actual nearest expiry formatter
    expiry = today.strftime("%d%b").upper()
    return f"NIFTY{expiry}{int(strike)}{opt_type}"

def place(symbol, qty, side):
    return kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=NFO,
        tradingsymbol=symbol,
        transaction_type=side,
        quantity=qty,
        product=kite.PRODUCT_MIS,
        order_type=kite.ORDER_TYPE_MARKET
    )

# ---------- STRATEGY ----------
def compute_levels():
    pdh, pdl = prev_day_hl()
    f15h, f15l = first_15m_hl()
    # combine zones
    resistance = max(pdh, f15h)
    support = min(pdl, f15l)
    return support, resistance

def pick_strikes(spot):
    atm = round_to_step(spot, STRIKE_STEP)
    ce_sell = atm + SELL_DIST
    pe_sell = atm - SELL_DIST
    ce_buy  = ce_sell + HEDGE_DIST
    pe_buy  = pe_sell - HEDGE_DIST
    return ce_sell, ce_buy, pe_sell, pe_buy

def enter_spread(kind, spot):
    ce_s, ce_b, pe_s, pe_b = pick_strikes(spot)

    if kind == "CE":
        s_sym = option_symbol(ce_s, "CE")
        b_sym = option_symbol(ce_b, "CE")
        place(b_sym, LOT_SIZE, "BUY")   # hedge first
        place(s_sym, LOT_SIZE, "SELL")
        state["positions"] = {
            "type":"CE",
            "sell": {"sym":s_sym, "entry": ltp(f"NFO:{s_sym}")},
            "buy":  {"sym":b_sym, "entry": ltp(f"NFO:{b_sym}")}
        }
        tg(f"SELL CE SPREAD: {s_sym} / HEDGE {b_sym}")

    elif kind == "PE":
        s_sym = option_symbol(pe_s, "PE")
        b_sym = option_symbol(pe_b, "PE")
        place(b_sym, LOT_SIZE, "BUY")
        place(s_sym, LOT_SIZE, "SELL")
        state["positions"] = {
            "type":"PE",
            "sell": {"sym":s_sym, "entry": ltp(f"NFO:{s_sym}")},
            "buy":  {"sym":b_sym, "entry": ltp(f"NFO:{b_sym}")}
        }
        tg(f"SELL PE SPREAD: {s_sym} / HEDGE {b_sym}")

    state["in_trade"] = True
    state["trades"] += 1

def exit_positions(reason):
    if not state["in_trade"]:
        return
    pos = state["positions"]
    # exit both legs
    place(pos["sell"]["sym"], LOT_SIZE, "BUY")
    place(pos["buy"]["sym"], LOT_SIZE, "SELL")

    # approximate PnL from sell leg
    cur = ltp(f"NFO:{pos['sell']['sym']}")
    entry = pos["sell"]["entry"]
    pnl = (entry - cur) * LOT_SIZE
    state["daily_pnl"] += pnl
    if pnl < 0:
        state["loss_count"] += 1

    tg(f"EXIT ({reason}) PnL≈{pnl:.0f}, DayPnL≈{state['daily_pnl']:.0f}")
    state["positions"] = {}
    state["in_trade"] = False

def manage_trade():
    pos = state["positions"]
    sell_sym = pos["sell"]["sym"]
    entry = pos["sell"]["entry"]
    cur = ltp(f"NFO:{sell_sym}")

    if cur >= entry * (1 + SL_PCT):
        exit_positions("SL")
    elif cur <= entry * (1 - TARGET_PCT):
        exit_positions("TARGET")

# ---------- MAIN LOOP ----------
def run():
    tg("Bot started ✅")

    support, resistance = compute_levels()

    while True:
        now = dt.datetime.now().time()
        if now >= FORCE_EXIT:
            exit_positions("TIME")
            tg("Day closed")
            break

        if state["kill"]:
            tg("Kill switch activated")
            break

        spot = get_spot()

        # dynamic day range (rolling)
        day_high = max(spot, resistance)
        day_low  = min(spot, support)

        if not is_range_day(day_high, day_low, spot):
            time.sleep(10); continue

        if not (ENTRY_START <= now <= ENTRY_END):
            time.sleep(10); continue

        if state["trades"] >= MAX_TRADES or state["loss_count"] >= 2 or state["daily_pnl"] <= -DAILY_MAX_LOSS:
            tg("Risk limits hit. Stopping entries.")
            break

        if not state["in_trade"]:
            c = last_candle()
            if near(spot, support) and bullish_rejection(c):
                enter_spread("PE", spot)
            elif near(spot, resistance) and bearish_rejection(c):
                enter_spread("CE", spot)
        else:
            manage_trade()

        time.sleep(15)

if __name__ == "__main__":
    run()