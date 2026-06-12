from trading_bot.kite_client import create_kite
from trading_bot.orders import KiteBroker, OrderRequest

symbol = "NIFTY2660223550CE"
qty = 65

kite = create_kite()
broker = KiteBroker(kite)

print("WARNING")
print("This is a REAL ORDER")
print("Symbol:", symbol)
print("Qty:", qty)

confirm = input("Type YES to place order: ")
if confirm != "YES":
    raise SystemExit("Order cancelled")

order_id = broker.place_order(
    OrderRequest(symbol=symbol, quantity=qty, transaction_type=kite.TRANSACTION_TYPE_SELL)
)
print("Order ID:", order_id)
