from kite_utils import get_atm_strike, get_kite_client, get_nifty_spot

kite = get_kite_client()
nifty_price = get_nifty_spot(kite)
atm = get_atm_strike(nifty_price)

print("NIFTY Price:", nifty_price)
print("ATM Strike:", atm)
