import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import pyotp
import requests
from dotenv import load_dotenv
from kiteconnect import KiteConnect

load_dotenv()


LOGGER = logging.getLogger("auto_login")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing env variable: {name}")
    return value


def optional_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value if value else None


API_KEY = require_env("KITE_API_KEY")
API_SECRET = require_env("KITE_API_SECRET")
USER_ID = require_env("KITE_USER_ID")
PASSWORD = require_env("KITE_PASSWORD")
TOTP_SECRET = require_env("KITE_TOTP_SECRET")
TG_TOKEN = optional_env("TELEGRAM_BOT_TOKEN")
TG_CHAT = optional_env("TELEGRAM_CHAT_ID")


def send_telegram(msg: str) -> None:
    if not TG_TOKEN or not TG_CHAT:
        return
    try:
        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TG_CHAT, "text": msg}, timeout=5)
    except Exception:
        LOGGER.exception("telegram error")


def get_totp() -> str:
    return pyotp.TOTP(TOTP_SECRET).now()


def post_json(session: requests.Session, url: str, data: dict) -> dict:
    response = session.post(url, data=data, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError(f"Request failed for {url}: {payload}")
    return payload


def auto_login() -> str:
    session = requests.Session()

    login_payload = post_json(
        session,
        "https://kite.zerodha.com/api/login",
        {"user_id": USER_ID, "password": PASSWORD},
    )
    request_id = login_payload["data"]["request_id"]

    post_json(
        session,
        "https://kite.zerodha.com/api/twofa",
        {
            "user_id": USER_ID,
            "request_id": request_id,
            "twofa_value": get_totp(),
        },
    )

    kite = KiteConnect(api_key=API_KEY)
    redirect_response = session.get(kite.login_url(), allow_redirects=True, timeout=10)
    redirect_response.raise_for_status()
    final_url = redirect_response.url

    if "request_token=" not in final_url:
        raise RuntimeError("request_token missing in redirect")

    request_token = final_url.split("request_token=")[1].split("&")[0]
    token_data = kite.generate_session(request_token, api_secret=API_SECRET)
    return token_data["access_token"]


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as tmp:
        tmp.write(content)
        temp_name = tmp.name
    os.replace(temp_name, path)


def update_env_access_token(env_path: Path, token: str) -> None:
    if not env_path.exists():
        raise FileNotFoundError(f"{env_path} not found")
    lines = env_path.read_text().splitlines()
    replaced = False
    output = []
    for line in lines:
        if line.startswith("KITE_ACCESS_TOKEN="):
            output.append(f"KITE_ACCESS_TOKEN={token}")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"KITE_ACCESS_TOKEN={token}")
    write_atomic(env_path, "\n".join(output) + "\n")


def run_with_retry(max_attempts: int = 3, delay_seconds: int = 5) -> str:
    for attempt in range(1, max_attempts + 1):
        try:
            return auto_login()
        except Exception:
            LOGGER.exception("login attempt %s failed", attempt)
            if attempt == max_attempts:
                raise
            time.sleep(delay_seconds * attempt)
    raise RuntimeError("unreachable")


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
    env_file = Path(".env")
    token_file = Path("access_token.txt")

    try:
        token = run_with_retry()
        write_atomic(token_file, token + "\n")
        update_env_access_token(env_file, token)
        send_telegram("✅ Zerodha login successful. Access token refreshed.")
        LOGGER.info("Access token refreshed")
    except Exception as exc:
        send_telegram(f"❌ Zerodha auto-login failed: {exc}")
        LOGGER.exception("auto-login failed")
        raise
