import argparse

from kite_utils import find_nearest_option_pair, get_kite_client

parser = argparse.ArgumentParser(description="Find nearest-expiry NIFTY CE/PE symbols for a strike")
parser.add_argument("strike", type=int, help="Strike price, e.g. 23550")
args = parser.parse_args()

kite = get_kite_client()
pair = find_nearest_option_pair(kite.instruments("NFO"), args.strike)

print("Expiry:", pair.expiry)
print("CE:", pair.ce_symbol)
print("PE:", pair.pe_symbol)
