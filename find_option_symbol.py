from datetime import date

from trading_bot.instruments import find_options_by_strike, get_nfo_instruments
from trading_bot.kite_client import create_kite

ATM_STRIKE = 23550

kite = create_kite()
instruments = get_nfo_instruments(kite)
ce, pe = find_options_by_strike(instruments, "NIFTY", ATM_STRIKE, min_expiry=date.today())

for ins in (ce, pe):
    print(ins["tradingsymbol"], ins["instrument_type"], ins["expiry"])
