import os, time, requests
import pyotp
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
USER_ID = os.getenv("KITE_USER_ID")
PASSWORD = os.getenv("KITE_PASSWORD")
TOTP_SECRET = os.getenv("KITE_TOTP_SECRET")

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID")


# 🔹 Telegram Alert
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_CHAT, "text": msg})
    except:
        pass


# 🔹 Generate TOTP
def get_totp():
    totp = pyotp.TOTP(TOTP_SECRET)
    return totp.now()


# 🔹 Auto Login Function
def auto_login():
    session = requests.Session()

    # Step 1: Login request
    login_url = "https://kite.zerodha.com/api/login"

    data = {
        "user_id": USER_ID,
        "password": PASSWORD
    }

    res = session.post(login_url, data=data)
    login_json = res.json()

    if login_json.get("status") != "success":
        raise Exception("Login failed")

    request_id = login_json["data"]["request_id"]

    # Step 2: TOTP verification
    totp = get_totp()

    twofa_url = "https://kite.zerodha.com/api/twofa"

    twofa_data = {
        "user_id": USER_ID,
        "request_id": request_id,
        "twofa_value": totp
    }

    res2 = session.post(twofa_url, data=twofa_data)
    twofa_json = res2.json()

    if twofa_json.get("status") != "success":
        raise Exception("TOTP failed")

    # Step 3: Get request_token from redirect
    kite = KiteConnect(api_key=API_KEY)

    login_redirect = kite.login_url()
    res3 = session.get(login_redirect, allow_redirects=True)

    final_url = res3.url

    if "request_token=" not in final_url:
        raise Exception("Request token not found")

    request_token = final_url.split("request_token=")[1].split("&")[0]

    # Step 4: Generate access token
    data = kite.generate_session(request_token, api_secret=API_SECRET)

    access_token = data["access_token"]

    return access_token


# 🔹 Save token to file
def save_token(token):
    with open("access_token.txt", "w") as f:
        f.write(token)


# 🔹 Update .env
def update_env(token):
    lines = []
    with open(".env", "r") as f:
        lines = f.readlines()

    with open(".env", "w") as f:
        for line in lines:
            if line.startswith("KITE_ACCESS_TOKEN"):
                f.write(f"KITE_ACCESS_TOKEN={token}\n")
            else:
                f.write(line)


# 🔹 MAIN
if __name__ == "__main__":
    try:
        token = auto_login()
        save_token(token)
        update_env(token)

        send_telegram("✅ Zerodha login successful. Token refreshed.")
        print("SUCCESS:", token)

    except Exception as e:
        send_telegram(f"❌ Login failed: {e}")
        print("ERROR:", e)