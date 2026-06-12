from kiteconnect import KiteConnect
from config import API_KEY

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Get NIFTY Spot Price
ltp = kite.ltp("NSE:NIFTY 50")

nifty_price = ltp["NSE:NIFTY 50"]["last_price"]

# Calculate ATM Strike
atm = round(nifty_price / 50) * 50

print("NIFTY Price:", nifty_price)
print("ATM Strike:", atm)