from kite_utils import get_kite_client, get_ltp, round_to_step

kite = get_kite_client()
sensex_price = get_ltp(kite, "BSE:SENSEX")
atm = round_to_step(sensex_price, 100)

print("SENSEX Price:", sensex_price)
print("ATM Strike:", atm)
