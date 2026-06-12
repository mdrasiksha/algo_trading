from kite_utils import get_kite_client

kite = get_kite_client()
margins = kite.margins()

print("Available Margin:")
print(margins["equity"]["available"]["live_balance"])
