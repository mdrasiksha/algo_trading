from kiteconnect import KiteConnect
from config import API_KEY

with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

def sell_option(symbol, qty):

    order_id = kite.place_order(
        variety=kite.VARIETY_REGULAR,
        exchange=kite.EXCHANGE_NFO,
        tradingsymbol=symbol,
        transaction_type=kite.TRANSACTION_TYPE_SELL,
        quantity=qty,
        product=kite.PRODUCT_MIS,
        order_type=kite.ORDER_TYPE_MARKET
    )

    return order_id


symbol = "NIFTY2660223550CE"
qty = 65

print("WARNING")
print("This is a REAL ORDER")
print("Symbol:", symbol)
print("Qty:", qty)

confirm = input("Type YES to place order: ")

if confirm != "YES":
    exit()

order_id = sell_option(symbol, qty)

print("Order ID:", order_id)