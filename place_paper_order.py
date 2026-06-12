from trading_bot.orders import OrderRequest, PaperBroker

symbol = "NIFTY2660223550CE"
qty = 65

broker = PaperBroker()
order_id = broker.place_order(
    OrderRequest(symbol=symbol, quantity=qty, transaction_type="SELL")
)
print("PAPER ORDER ID:", order_id)
