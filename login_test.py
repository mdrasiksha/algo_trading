from kiteconnect import KiteConnect

from trading_bot.settings import load_settings

settings = load_settings(require_token=False)
kite = KiteConnect(api_key=settings.api_key)

print(kite.login_url())
