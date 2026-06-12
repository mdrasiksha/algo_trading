from trading_bot.kite_client import create_kite, kite_retry

kite = create_kite()


@kite_retry()
def get_live_balance() -> float:
    margins = kite.margins()
    return float(margins["equity"]["available"]["live_balance"])


print("Available Margin:")
print(get_live_balance())
