# Zerodha Kite Connect Options Bot: Production Readiness Review

## A. Current architecture review

The repository started as a collection of flat, single-purpose scripts. Most files repeated the same sequence: import `KiteConnect`, read `access_token.txt`, create a client, and call one API. That is useful while learning Kite Connect, but it is risky for automated trading because authentication, retries, logging, risk controls, and order safety were not centralized.

Incremental refactoring now adds a reusable `trading_bot` package while keeping the original scripts as entry points:

- `trading_bot/settings.py` centralizes environment-based configuration and ignored token-file handling.
- `trading_bot/kite_client.py` centralizes authenticated client creation and transient network retries.
- `trading_bot/market_data.py` centralizes LTP, ATM strike, and option premium retrieval.
- `trading_bot/instruments.py` centralizes NFO instrument master lookup, option selection, and lot-size lookup.
- `trading_bot/risk.py` centralizes quantity, daily loss, stop-loss, and target calculations.
- `trading_bot/orders.py` provides `PaperBroker` and `KiteBroker` order abstractions.
- `trading_bot/notifications.py` adds Telegram alert support.
- `trading_bot/logging_config.py` adds console and rotating-file logging.

## B. Security review

| Area | Status | Findings | Action items |
| --- | --- | --- | --- |
| Authentication security | ⚠ Needs Improvement | Code now supports environment variables and local ignored token files, but a real `access_token.txt` and local `config.py` existed in the working tree and were previously tracked. | Rotate the Kite access token immediately, invalidate active sessions if needed, keep `config.py` and `access_token.txt` untracked, and move all CI/CD secrets to GitHub Actions secrets. |
| API keys and secrets in Git | ⚠ Needs Improvement | `.gitignore` excludes secrets, but tracked IDE files, `config.py`, `access_token.txt`, and `__pycache__` were present in the index. | Remove tracked secrets/cache/IDE files from Git and consider repository history cleanup if a real token was pushed to a remote. |
| GitHub secrets management | ❌ Missing | No GitHub Actions workflow or documented secret names existed. | Store `KITE_API_KEY`, `KITE_API_SECRET`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID` as GitHub/environment secrets; never write access tokens to CI logs. |
| Token refresh workflow | ⚠ Needs Improvement | `generate_token.py` performs daily request-token exchange and writes with owner-only permissions, but there is no guided login CLI, token expiry validation, or session audit trail. | Add a `login` command that prints login URL, accepts request token, validates profile, stores token securely, and alerts on token failure. |

## C. Missing components and risk review

| Production item | Status | Findings | Action items |
| --- | --- | --- | --- |
| Order placement safety | ⚠ Needs Improvement | Live test order still requires manual `YES`, and `KiteBroker` centralizes live placement, but no pre-trade checklist blocks bad market states yet. | Add pre-order validations for paper/live mode, quantity, product, exchange, tradingsymbol, margin, market hours, holiday, daily loss, and duplicate order checks. |
| Position sizing | ⚠ Needs Improvement | `RiskLimits` limits lots and `calculate_quantity` enforces max lots, but sizing is not connected to margin, volatility, or daily loss budget. | Compute quantity from available margin, lot size, max daily loss, and per-trade SL; default to one lot for live 0DTE until proven safe. |
| Stop-loss protection | ⚠ Needs Improvement | Combined premium SL calculation exists, but no live position monitor or protective exit order loop exists. | Add a monitor that polls positions/quotes, exits both legs on combined SL, and sends Telegram alerts before and after exit. |
| Profit target execution | ⚠ Needs Improvement | Combined target calculation exists, but execution logic is missing. | Add target rule support and ensure target exits are mutually exclusive with SL and square-off. |
| Daily loss limits | ⚠ Needs Improvement | `ensure_daily_loss_not_breached` exists, but realized/unrealized P&L aggregation is not wired to Kite positions. | Poll `kite.positions()`, compute realized and mark-to-market P&L, block entries after breach, and force square-off if configured. |
| Auto square-off | ❌ Missing | No scheduler closes positions before market close. | Add a market-close guard, e.g., square off all bot-tagged MIS NFO positions by 15:15 IST, with retry and alert escalation. |
| Position monitoring | ❌ Missing | No long-running monitor loop or state store exists. | Add a bot state file/database with strategy ID, order IDs, entry premiums, current status, and exit reason. |
| Margin checks | ⚠ Needs Improvement | `check_margin.py` reads live balance, but order flow does not call margin checks. | Use `kite.order_margins()` when available and compare with live balance plus a safety buffer before placing each order basket. |
| Instrument lookup | ⚠ Needs Improvement | Instrument lookup is centralized and filters expired contracts, but it downloads the full NFO master each run and does not cache. | Cache NFO instruments daily, validate expiry is the intended 0DTE/weekly expiry, and handle symbol format changes. |
| ATM strike selection | ⚠ Needs Improvement | ATM strike helper exists for NIFTY/SENSEX, but it does not handle locked markets, stale quotes, or custom offsets. | Add quote timestamp/staleness checks, configurable strike step, and support for ATM±offset strategies. |
| Option premium retrieval | ⚠ Needs Improvement | Premiums are fetched in one batched `ltp` call. | Add quote validation for missing symbols, zero prices, wide spreads, stale data, and circuit/illiquid conditions. |
| Telegram alerts | ⚠ Needs Improvement | Telegram sender exists, but strategy events are not fully wired. | Send alerts for startup, login failure, entry, rejected order, SL hit, target hit, square-off, daily loss breach, and unhandled exceptions. |
| Exception handling | ⚠ Needs Improvement | Transient network retry and token-failure handling are centralized, but script-level recovery is still basic. | Add top-level guarded runner that catches expected Kite exceptions, sends alerts, persists state, and exits safely. |
| Logging | ⚠ Needs Improvement | Rotating file and console logging exist. | Replace remaining `print` statements in production runner with structured logs and include strategy ID/order IDs. |
| Market holiday handling | ❌ Missing | No NSE holiday calendar or trading-session validation exists. | Add an exchange calendar source and block entries on holidays/special sessions; still allow emergency square-off when positions exist. |
| Network failure recovery | ⚠ Needs Improvement | Kite network calls retry transient errors. | Add idempotent order reconciliation: after timeout, check order book/positions before placing another order. |
| Zerodha API rate limits | ⚠ Needs Improvement | Batched LTP is used for premiums, but there is no rate limiter. | Add a per-endpoint throttle, cache instrument master, avoid tight polling, and prefer KiteTicker websocket for live monitoring. |
| Paper trading mode | ⚠ Needs Improvement | `PaperBroker` returns synthetic order IDs and logs intent. | Add fills, slippage model, P&L accounting, and persistence so paper and live mode share the same strategy engine. |

## D. Recommended production-grade folder structure

```text
algo_trading/
  trading_bot/
    __init__.py
    settings.py              # env/config loading, token file helpers
    logging_config.py        # console + rotating-file logging
    kite_client.py           # KiteConnect factory, retries, rate limits
    instruments.py           # instrument master cache and lookup
    market_data.py           # quotes, ATM strike, premium helpers
    orders.py                # paper/live broker abstractions
    risk.py                  # sizing, daily loss, SL/target checks
    notifications.py         # Telegram and future alert channels
    strategy/
      short_straddle.py      # NIFTY 0DTE option-selling rules
      monitor.py             # SL/target/square-off loop
    storage/
      state_store.py         # JSON/SQLite state and audit trail
    cli.py                   # login, paper-run, live-run, diagnostics
  tests/
    unit/
    integration/             # mocked Kite integration tests
  docs/
    production_readiness_checklist.md
  .env.example
  config.example.py
  requirements.txt
```

Keep the current small scripts during migration, but treat them as diagnostics only. Production should enter through a single CLI that always initializes config, logging, risk limits, paper/live mode, notifier, and state recovery.

## E. Recommended implementation order

1. **Secrets cleanup and token rotation**: remove tracked secrets/IDE/cache files, rotate the exposed access token, and use `.env`/GitHub secrets.
2. **Single bot runner**: create one CLI command for `login`, `paper-run`, `live-run`, `square-off`, and `diagnostics`.
3. **State model**: persist strategy date, mode, symbols, quantities, order IDs, entry premiums, SL, target, and exit reason.
4. **Paper engine**: make paper trading behavior match live flow with simulated fills and P&L.
5. **Pre-trade risk gate**: validate market day, time window, margin, lot size, max daily loss, open positions, and duplicate entries.
6. **Live order reconciliation**: after every order, reconcile with order book and positions; never blindly retry live orders.
7. **Monitoring loop**: implement combined premium SL/target, daily loss kill switch, and time-based square-off.
8. **Telegram alert coverage**: alert on all lifecycle events and unhandled exceptions.
9. **Testing**: add unit tests with fake broker/fake Kite and integration tests that never place real orders.
10. **Observability and deployment**: add structured logs, metrics, runbook, and supervisor/systemd/cloud scheduler with IST timezone.

## F. Sample code improvements

### Secure settings

```python
from trading_bot.settings import load_settings

settings = load_settings(require_token=True)
```

### Centralized Kite client with retries

```python
from trading_bot.kite_client import create_kite

kite = create_kite(settings)
```

### Paper/live order abstraction

```python
from trading_bot.orders import KiteBroker, PaperBroker, OrderRequest

broker = PaperBroker() if settings.paper_trading else KiteBroker(kite)
order_id = broker.place_order(
    OrderRequest(symbol="NIFTY...CE", quantity=65, transaction_type="SELL")
)
```

### Risk-first stop-loss calculation

```python
from trading_bot.risk import RiskLimits, combined_stop_loss

limits = RiskLimits(max_daily_loss=2000, max_lots=1, stop_loss_multiplier=1.6)
sl = combined_stop_loss(ce_price, pe_price, limits)
```

## Fully automated NIFTY 0DTE option-selling roadmap

- **Phase 1: Safe diagnostics**: login, profile check, margin check, NFO cache, ATM strike, option symbol selection, premium retrieval.
- **Phase 2: Paper trading**: one-lot short straddle/strangle in paper mode, state persistence, synthetic fills, SL/target/square-off logic.
- **Phase 3: Live guarded single lot**: enable live mode only behind explicit config, strict market window, margin buffer, max loss, and Telegram approval/alerts.
- **Phase 4: Resilience**: websocket quotes, rate limiter, order reconciliation, crash recovery, and duplicate-order prevention.
- **Phase 5: Strategy hardening**: backtests, walk-forward paper logs, expiry-day filters, IV/spread filters, event-day blocklist, and capital-based sizing.

## Production readiness checklist

| Item | Status | Make production-ready by doing this |
| --- | --- | --- |
| Authentication security | ⚠ Needs Improvement | Use environment variables/secrets, rotate exposed token, validate daily session before trading. |
| Order placement safety | ⚠ Needs Improvement | Gate every order with market hours, holidays, margin, lot size, mode, and duplicate checks. |
| Position sizing | ⚠ Needs Improvement | Link lot count to max daily loss, margin, and SL; keep live default at one lot. |
| Stop-loss protection | ⚠ Needs Improvement | Add a live monitor that exits all bot positions when combined premium SL is hit. |
| Exception handling | ⚠ Needs Improvement | Add top-level exception guard, alerting, state persistence, and safe shutdown behavior. |
| Logging | ⚠ Needs Improvement | Use rotating structured logs in the production runner and remove ad-hoc prints. |
| Telegram alerts | ⚠ Needs Improvement | Wire alerts to startup, entry, exit, SL, target, square-off, and failures. |
| Daily loss limits | ⚠ Needs Improvement | Compute Kite P&L continuously and block/exit when daily loss is breached. |
| Market holiday handling | ❌ Missing | Add NSE calendar and block entries on non-trading days/special sessions. |
| Network failure recovery | ⚠ Needs Improvement | Add reconciliation after timeout before retrying live orders. |
| Zerodha API rate limits | ⚠ Needs Improvement | Add throttling, cache instruments, and use websocket data for monitoring. |
| Paper trading mode | ⚠ Needs Improvement | Persist paper fills/P&L and run the same strategy path as live mode. |
| GitHub secrets management | ❌ Missing | Add documented secret names and ensure workflows never echo secrets. |
