from kiteconnect import KiteConnect
from config import API_KEY, API_SECRET

kite = KiteConnect(api_key=API_KEY)

request_token = input("Request token: ").strip()

data = kite.generate_session(
    request_token=request_token,
    api_secret=API_SECRET
)

access_token = data["access_token"]

with open("access_token.txt", "w") as f:
    f.write(access_token)

print("Access token saved successfully!")