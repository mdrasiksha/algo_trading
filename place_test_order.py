import argparse

from kite_utils import get_kite_client

parser = argparse.ArgumentParser(description="Place a real Kite MIS market order after explicit confirmation")
parser.add_argument("symbol", help="NFO trading symbol")
parser.add_argument("qty", type=int, help="Quantity")
parser.add_argument("side", choices=["BUY", "SELL"], help="Transaction side")
args = parser.parse_args()

kite = get_kite_client()

print("WARNING")
print("This is a REAL ORDER")
print("Symbol:", args.symbol)
print("Qty:", args.qty)
print("Side:", args.side)

confirm = input("Type YES to place order: ")
if confirm != "YES":
    raise SystemExit("Order cancelled")

order_id = kite.place_order(
    variety=kite.VARIETY_REGULAR,
    exchange=kite.EXCHANGE_NFO,
    tradingsymbol=args.symbol,
    transaction_type=args.side,
    quantity=args.qty,
    product=kite.PRODUCT_MIS,
    order_type=kite.ORDER_TYPE_MARKET,
)

print("Order ID:", order_id)
