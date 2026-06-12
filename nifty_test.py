from kite_utils import get_kite_client

kite = get_kite_client()
print(kite.ltp("NSE:NIFTY 50"))
