from trading_bot.kite_client import create_kite, kite_retry

kite = create_kite()


@kite_retry()
def get_profile():
    return kite.profile()


print(get_profile())
