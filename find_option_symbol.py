from kiteconnect import KiteConnect
from config import API_KEY

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

ATM_STRIKE = 23550

instruments = kite.instruments("NFO")

for ins in instruments:
    if (
        ins["name"] == "NIFTY"
        and ins["strike"] == ATM_STRIKE
        and ins["instrument_type"] in ["CE", "PE"]
    ):
        print(
            ins["tradingsymbol"],
            ins["instrument_type"],
            ins["expiry"]
        )