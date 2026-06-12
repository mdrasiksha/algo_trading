import argparse

parser = argparse.ArgumentParser(description="Record a paper trade without sending it to Kite")
parser.add_argument("symbol", help="NFO trading symbol")
parser.add_argument("qty", type=int, help="Quantity")
parser.add_argument("side", choices=["BUY", "SELL"], help="Transaction side")
args = parser.parse_args()

print(f"PAPER TRADE: {args.side} {args.qty} {args.symbol}")
