from kiteconnect import KiteConnect
from config import API_KEY

kite = KiteConnect(api_key=API_KEY)

with open("access_token.txt") as f:
    access_token = f.read().strip()

kite.set_access_token(access_token)

profile = kite.profile()

print(profile)