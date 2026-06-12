from trading_bot.kite_client import create_kite
from trading_bot.market_data import NIFTY_SPOT, get_last_price

kite = create_kite()
print(get_last_price(kite, NIFTY_SPOT))
