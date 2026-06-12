import argparse

from kite_utils import get_kite_client

parser = argparse.ArgumentParser(description="Check NFO lot size for a trading symbol")
parser.add_argument("symbol", help="NFO trading symbol, e.g. NIFTY2660223550CE")
args = parser.parse_args()

kite = get_kite_client()

for instrument in kite.instruments("NFO"):
    if instrument["tradingsymbol"] == args.symbol:
        print("Lot Size:", instrument["lot_size"])
        break
else:
    raise SystemExit(f"Symbol not found: {args.symbol}")
