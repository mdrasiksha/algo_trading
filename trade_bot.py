from trading_bot.kite_client import create_kite, kite_retry
from trading_bot.logging_config import configure_logging
from trading_bot.notifications import TelegramNotifier
from trading_bot.settings import load_settings

configure_logging()
settings = load_settings()
notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
kite = create_kite(settings)


@kite_retry()
def get_profile():
    return kite.profile()


profile = get_profile()
notifier.send(f"Kite profile loaded for {profile.get('user_name', 'unknown user')}")
print(profile)
