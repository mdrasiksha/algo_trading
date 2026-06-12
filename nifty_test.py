from kiteconnect import KiteConnect
from config import API_KEY

kite = KiteConnect(api_key=API_KEY)

with open("access_token.txt") as f:
    kite.set_access_token(f.read().strip())

print(kite.ltp("NSE:NIFTY 50"))