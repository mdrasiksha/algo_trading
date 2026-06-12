from kiteconnect import KiteConnect
from config import API_KEY

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

print(kite.ltp("NSE:NIFTY 50"))