from trading_bot.instruments import get_nfo_instruments, lot_size_for_symbol
from trading_bot.kite_client import create_kite

SYMBOL = "NIFTY2660223550CE"

kite = create_kite()
instruments = get_nfo_instruments(kite)
print("Lot Size:", lot_size_for_symbol(instruments, SYMBOL))
