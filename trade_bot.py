from kiteconnect import KiteConnect
from config import API_KEY

with open("access_token.txt") as f:
    access_token = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(access_token)

print(kite.profile())