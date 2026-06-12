from kiteconnect import KiteConnect
from config import API_KEY

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

ltp = kite.ltp("BSE:SENSEX")

sensex_price = ltp["BSE:SENSEX"]["last_price"]

atm = round(sensex_price / 100) * 100

print("SENSEX Price:", sensex_price)
print("ATM Strike:", atm)