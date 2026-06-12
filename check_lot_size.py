from kiteconnect import KiteConnect
from config import API_KEY

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

instruments = kite.instruments("NFO")

symbol = "NIFTY2660223550CE"

for ins in instruments:
    if ins["tradingsymbol"] == symbol:
        print("Lot Size:", ins["lot_size"])
        break