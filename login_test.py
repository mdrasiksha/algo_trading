from kiteconnect import KiteConnect

from config import API_KEY

kite = KiteConnect(api_key=API_KEY)
print(kite.login_url())
