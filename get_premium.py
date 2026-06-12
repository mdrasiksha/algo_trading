from kiteconnect import KiteConnect
from config import API_KEY

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Step 1: Get NIFTY Spot Price
ltp = kite.ltp("NSE:NIFTY 50")
nifty_price = ltp["NSE:NIFTY 50"]["last_price"]

# Step 2: Calculate ATM Strike
atm = int(round(nifty_price / 50) * 50)

print(f"NIFTY Price: {nifty_price}")
print(f"ATM Strike: {atm}")

# Step 3: Find nearest expiry CE and PE
instruments = kite.instruments("NFO")

ce_symbol = None
pe_symbol = None
nearest_expiry = None

for ins in instruments:
    if (
        ins["name"] == "NIFTY"
        and ins["strike"] == atm
        and ins["instrument_type"] in ["CE", "PE"]
    ):
        if nearest_expiry is None:
            nearest_expiry = ins["expiry"]

        if ins["expiry"] == nearest_expiry:
            if ins["instrument_type"] == "CE":
                ce_symbol = ins["tradingsymbol"]

            if ins["instrument_type"] == "PE":
                pe_symbol = ins["tradingsymbol"]

print("CE:", ce_symbol)
print("PE:", pe_symbol)

# Step 4: Fetch premiums
quotes = kite.ltp([
    f"NFO:{ce_symbol}",
    f"NFO:{pe_symbol}"
])

ce_price = quotes[f"NFO:{ce_symbol}"]["last_price"]
pe_price = quotes[f"NFO:{pe_symbol}"]["last_price"]

combined = ce_price + pe_price

# Step 5: Calculate SL
sl_level = combined * 1.60

print()
print(f"CE Premium = {ce_price}")
print(f"PE Premium = {pe_price}")
print(f"Combined Premium = {combined}")
print(f"60% SL Level = {sl_level}")