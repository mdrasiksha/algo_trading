from datetime import date

from trading_bot.instruments import find_options_by_strike, get_nfo_instruments
from trading_bot.kite_client import create_kite
from trading_bot.market_data import NIFTY_SPOT, get_atm_strike, get_option_premiums
from trading_bot.risk import RiskLimits, combined_stop_loss

kite = create_kite()

# Step 1: Get NIFTY Spot Price and ATM strike
nifty_price, atm = get_atm_strike(kite, NIFTY_SPOT, 50)
print(f"NIFTY Price: {nifty_price}")
print(f"ATM Strike: {atm}")

# Step 2: Find nearest unexpired CE and PE
instruments = get_nfo_instruments(kite)
ce, pe = find_options_by_strike(instruments, "NIFTY", atm, min_expiry=date.today())
ce_symbol = ce["tradingsymbol"]
pe_symbol = pe["tradingsymbol"]

print("CE:", ce_symbol)
print("PE:", pe_symbol)

# Step 3: Fetch premiums in one batched API call
ce_price, pe_price = get_option_premiums(kite, ce_symbol, pe_symbol)
combined = ce_price + pe_price
sl_level = combined_stop_loss(ce_price, pe_price, RiskLimits(max_daily_loss=0.0))

print()
print(f"CE Premium = {ce_price}")
print(f"PE Premium = {pe_price}")
print(f"Combined Premium = {combined}")
print(f"60% SL Level = {sl_level}")
