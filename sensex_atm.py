from trading_bot.kite_client import create_kite
from trading_bot.market_data import SENSEX_SPOT, get_atm_strike

kite = create_kite()
sensex_price, atm = get_atm_strike(kite, SENSEX_SPOT, 100)

print("SENSEX Price:", sensex_price)
print("ATM Strike:", atm)
