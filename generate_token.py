from kiteconnect import KiteConnect

from config import API_KEY, API_SECRET

if not API_SECRET:
    raise ValueError("Missing required environment variable: KITE_API_SECRET")

kite = KiteConnect(api_key=API_KEY)
request_token = input("Request token: ").strip()

data = kite.generate_session(request_token=request_token, api_secret=API_SECRET)
access_token = data["access_token"]

print("Access token generated successfully.")
print("Set it in your local .env as:")
print(f"KITE_ACCESS_TOKEN={access_token}")
