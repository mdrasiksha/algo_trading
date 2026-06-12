from trading_bot.kite_client import create_kite
from trading_bot.market_data import NIFTY_SPOT, get_atm_strike

kite = create_kite()
nifty_price, atm = get_atm_strike(kite, NIFTY_SPOT, 50)

print("NIFTY Price:", nifty_price)
print("ATM Strike:", atm)
