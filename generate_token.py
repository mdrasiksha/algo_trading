from kiteconnect import KiteConnect

from trading_bot.settings import load_settings, write_access_token

settings = load_settings(require_token=False, require_secret=True)
kite = KiteConnect(api_key=settings.api_key)

request_token = input("Request token: ").strip()

data = kite.generate_session(
    request_token=request_token,
    api_secret=settings.api_secret,
)

access_token = data["access_token"]
write_access_token(access_token, settings.access_token_path)

print("Access token saved successfully!")
