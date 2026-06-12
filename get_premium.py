from kite_utils import get_atm_strike, get_kite_client, get_ltp, get_nifty_spot, get_option_pair_for_atm

kite = get_kite_client()
nifty_price = get_nifty_spot(kite)
atm = get_atm_strike(nifty_price)
pair = get_option_pair_for_atm(kite, nifty_price)

ce_instrument = f"NFO:{pair.ce_symbol}"
pe_instrument = f"NFO:{pair.pe_symbol}"
ce_price = get_ltp(kite, ce_instrument)
pe_price = get_ltp(kite, pe_instrument)
combined = ce_price + pe_price
sl_level = combined * 1.60

print(f"NIFTY Price: {nifty_price}")
print(f"ATM Strike: {atm}")
print("Expiry:", pair.expiry)
print("CE:", pair.ce_symbol)
print("PE:", pair.pe_symbol)
print()
print(f"CE Premium = {ce_price}")
print(f"PE Premium = {pe_price}")
print(f"Combined Premium = {combined}")
print(f"60% SL Level = {sl_level}")
