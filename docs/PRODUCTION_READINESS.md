# Zerodha Kite Connect NIFTY Option-Selling Bot Review

## A. Current architecture review

The repository is a flat collection of scripts plus one larger `bot.py` strategy runner. Small utilities handle login URL generation, token generation, connection tests, ATM strike discovery, option symbol lookup, premium checks, lot-size checks, margin checks, and test order placement. Shared Kite client creation and common instrument helpers now live in `kite_utils.py`, while environment-backed configuration lives in `config.py`.

### Findings

| Area | Status | Notes | Action items |
|---|---:|---|---|
| Folder structure | ⚠ Needs Improvement | Flat scripts are easy to start with but hard to test, package, and deploy. | Move toward `src/algo_trading/` package, `scripts/`, `tests/`, and `docs/`. |
| Strategy isolation | ⚠ Needs Improvement | `bot.py` mixes strategy, broker access, risk checks, notifications, and runtime loop. | Split into strategy, broker adapter, risk manager, execution manager, and notification modules. |
| Duplicate Kite setup | ✅ Ready | Utility scripts now use `kite_utils.get_kite_client()` instead of repeating token file reads. | Keep new scripts on the shared helper. |
| Paper trading | ⚠ Needs Improvement | `bot.py` defaults to paper fills using LTP and avoids live orders when `PAPER_TRADING=true`. | Replace LTP fills with a paper broker simulator that models bid/ask, slippage, and rejected orders. |
| CLI ergonomics | ⚠ Needs Improvement | Several scripts now accept arguments instead of hard-coded symbols. | Add a single CLI entry point with subcommands. |
| Tests | ❌ Missing | No automated test suite exists. | Add unit tests for strike rounding, option lookup, risk limits, paper broker, and exit logic. |

## B. Security review

### Authentication security

| Item | Status | Evidence / risk | Action items |
|---|---:|---|---|
| Hard-coded API key/secret | ⚠ Needs Improvement | `config.py` now reads `KITE_API_KEY`, `KITE_API_SECRET`, and `KITE_ACCESS_TOKEN` from env; previous tracked history may still contain secrets/placeholders. | Rotate any real keys ever committed; use GitHub secret scanning; purge history if real values were exposed. |
| Tracked `.env` | ❌ Missing | `.env` was already tracked, so `.gitignore` alone did not protect it. | Remove from Git index and keep only `.env.example`; rotate secrets if real values were committed. |
| Tracked access token | ❌ Missing | `access_token.txt` was already tracked. | Remove from Git index; store access tokens in `.env`, an encrypted secret store, or short-lived runtime storage. |
| Token refresh workflow | ⚠ Needs Improvement | `auto_login.py` automates login and writes the token locally, but it updates `.env` directly and depends on credentials/TOTP secret. | Prefer manual request-token flow or a secure scheduler with encrypted secrets; never commit updated `.env`. |
| GitHub secrets management | ❌ Missing | No CI workflow or documented secret policy. | Store only secret names in code; configure GitHub Actions secrets; add pre-commit secret scanning. |

## C. Missing components for safe 0DTE option selling

| Capability | Status | Current state | Action items |
|---|---:|---|---|
| Authentication | ⚠ Needs Improvement | Env-based client creation and login scripts exist. | Add token expiry detection, daily token refresh runbook, and failure alerts. |
| Token refresh workflow | ⚠ Needs Improvement | `auto_login.py` retries login and Telegram alerts. | Move token writes out of project root; encrypt at rest; add audit logs. |
| Margin checks | ⚠ Needs Improvement | Main bot supports a `MIN_AVAILABLE_MARGIN` floor before entry. | Use Zerodha order margin APIs/basket margins for exact spread margin before placing orders. |
| Instrument lookup | ✅ Ready | Shared nearest-expiry NIFTY CE/PE lookup helper exists. | Cache instruments daily and invalidate on expiry/holiday changes. |
| ATM strike selection | ✅ Ready | Shared `get_atm_strike()` rounds to configured step. | Unit-test edge cases and strike step changes. |
| Option premium retrieval | ✅ Ready | Shared `get_ltp()` and `get_option_pair_for_atm()` exist. | Prefer quote depth for live entries/exits, not just LTP. |
| Order placement safety | ⚠ Needs Improvement | Live utility requires confirmation; bot has paper-mode default and retries. | Add idempotency, order tags, max quantity limits, kill switch file, and partial-fill handling. |
| Position monitoring | ⚠ Needs Improvement | `bot.py` estimates open PnL and exits on hard SL/target. | Reconcile against Kite positions every loop; persist open state across restarts. |
| Stop-loss execution | ⚠ Needs Improvement | Software SL exits when premium or spread PnL threshold is hit. | Add broker-side SL/SL-M or GTT-style contingency where allowed; protect against process/network failure. |
| Profit target execution | ⚠ Needs Improvement | Software target exists. | Add configurable target modes and trailing logic only after backtesting. |
| Auto square-off | ⚠ Needs Improvement | Force-exit time is implemented. | Add exchange holiday/half-day calendar and a final position reconciliation after exits. |
| Telegram notifications | ⚠ Needs Improvement | Basic de-duplicated Telegram sends exist. | Add alert severities, retries, startup config summary, heartbeat, and critical manual-action alerts. |
| Daily max loss control | ⚠ Needs Improvement | Runtime PnL limit exists but is in-memory only. | Persist daily realized/unrealized PnL and include broker positions/orders in loss calculation. |
| Market holiday handling | ❌ Missing | No exchange calendar. | Add NSE trading calendar check before login/trading; support special sessions. |
| Network failure recovery | ⚠ Needs Improvement | API retry with exponential backoff exists. | Add circuit breaker, offline mode, heartbeat, and post-reconnect reconciliation. |
| Zerodha API rate limits | ⚠ Needs Improvement | Poll interval and retries exist, but no rate limiter. | Add per-endpoint throttling and batch LTP/quote calls. |

## D. Refactored folder structure

Recommended target structure without a big-bang rewrite:

```text
algo_trading/
├── README.md
├── requirements.txt
├── .env.example
├── docs/
│   └── PRODUCTION_READINESS.md
├── scripts/
│   ├── generate_token.py
│   ├── check_margin.py
│   ├── get_premium.py
│   └── place_test_order.py
├── src/
│   └── algo_trading/
│       ├── __init__.py
│       ├── config.py
│       ├── broker/
│       │   ├── kite_client.py
│       │   ├── paper_broker.py
│       │   └── order_manager.py
│       ├── marketdata/
│       │   ├── instruments.py
│       │   └── quotes.py
│       ├── risk/
│       │   ├── limits.py
│       │   ├── sizing.py
│       │   └── kill_switch.py
│       ├── strategies/
│       │   └── nifty_0dte_credit_spread.py
│       ├── notifications/
│       │   └── telegram.py
│       └── runtime/
│           ├── state_store.py
│           └── scheduler.py
└── tests/
    ├── test_instruments.py
    ├── test_risk_limits.py
    └── test_paper_broker.py
```

## E. Recommended implementation order

1. **Secure the repo first**: untrack `.env`, `access_token.txt`, `.idea/`, and `__pycache__/`; rotate any exposed keys/tokens.
2. **Add tests around current behavior**: strike rounding, option lookup, paper order path, risk limit path, force-exit path.
3. **Extract broker interfaces**: create a `Broker` protocol with Kite and paper implementations.
4. **Persist runtime state**: save open position, daily PnL, order IDs, and kill-switch status locally or in a small database.
5. **Add exact margin/risk checks**: use basket/order margin checks before spread entry; hard cap lot size and per-trade max loss.
6. **Improve execution safety**: order tags, idempotency keys, partial-fill recovery, and broker-position reconciliation.
7. **Add market calendar**: skip holidays and special non-trading sessions; enforce square-off earlier on short sessions.
8. **Add production observability**: structured logs, alert levels, heartbeat, and critical manual intervention alerts.
9. **Backtest/paper trade strategy**: record fills, slippage, rejected orders, and daily drawdown before enabling live mode.
10. **Enable live mode only by explicit deploy flag**: `PAPER_TRADING=false` plus manual approval and startup summary.

## F. Sample code improvements included

- `config.py` now has env-backed settings and helpers instead of hard-coded credentials.
- `kite_utils.py` centralises Kite client creation, LTP reads, ATM strike rounding, and nearest-expiry CE/PE lookup.
- Utility scripts now reuse shared helpers and avoid checked-in `access_token.txt` reads.
- `bot.py` now defaults to paper trading, supports `MIN_AVAILABLE_MARGIN`, logs paper fills, and calculates spread max risk more realistically as width minus net credit.


## Kite Connect API best-practice checks

Current recommendations are aligned to the official Kite Connect documentation reviewed on 2026-06-12:

- Use the official margin APIs before live entries: `/margins/orders` for order-level checks and `/margins/basket` for spread/basket margin benefits. See <https://kite.trade/docs/connect/v3/margins/>.
- Use order status reconciliation after placement because exchange orders can be open, partially filled, rejected, or cancelled. See <https://kite.trade/docs/connect/v3/orders/>.
- For market/SL-M orders, evaluate Kite's market-protection support where appropriate and avoid assuming market orders always fill at LTP. See <https://kite.trade/docs/connect/v3/orders/>.
- Add daily order-count guardrails; Zerodha documents an order-placement risk limit per user/API key. See <https://kite.trade/docs/connect/v3/exceptions/>.
- Keep `api_secret` only on a secure backend/runtime, not in client apps. See <https://kite.trade/docs/connect/v3/>.

## Production readiness checklist

| Checklist item | Status | Action items |
|---|---:|---|
| Authentication security | ⚠ Needs Improvement | Keep secrets in environment/secret manager; rotate exposed values; add token-expiry checks. |
| Order placement safety | ⚠ Needs Improvement | Default paper mode exists; add idempotency, tags, partial-fill recovery, quantity caps, and kill-switch file. |
| Position sizing | ⚠ Needs Improvement | Single lot configurable via `DEFAULT_LOT_SIZE`; add account-risk-based sizing and lot-size validation from instruments. |
| Stop-loss protection | ⚠ Needs Improvement | Software SL exists; add broker-side contingency and state persistence. |
| Exception handling | ⚠ Needs Improvement | API/order retries exist; add typed exceptions, circuit breaker, and reconciliation after errors. |
| Logging | ⚠ Needs Improvement | Basic console logging exists; add rotating files/JSON logs and order/audit trails. |
| Telegram alerts | ⚠ Needs Improvement | Basic alerts exist; add heartbeat, severity, retry/backoff, and rate-limited critical alerts. |
| Daily loss limits | ⚠ Needs Improvement | In-memory limit exists; persist PnL and include Kite-reported positions. |
| Market holiday handling | ❌ Missing | Integrate NSE calendar and skip non-trading days/special sessions. |
| Network failure recovery | ⚠ Needs Improvement | Basic retries exist; add reconnect reconciliation and fail-safe exit workflow. |
| Zerodha API rate limits | ⚠ Needs Improvement | Add central rate limiter and batch quotes. |
| Paper trading mode | ⚠ Needs Improvement | Default paper path exists; build realistic paper broker and trade journal. |
| GitHub secrets management | ❌ Missing | Add secret scanning, remove tracked local files, configure GitHub Actions secrets, document rotation process. |

## Roadmap to a fully automated NIFTY 0DTE option-selling bot

1. **Week 1 - Safety baseline**: repo secret cleanup, paper-mode-only default, unit tests, instrument cache, config validation.
2. **Week 2 - Broker abstraction**: Kite broker + paper broker behind the same interface, order tags, reconciliation loop.
3. **Week 3 - Risk engine**: daily loss persistence, max trade count, max lots, spread width checks, margin pre-check, kill switch.
4. **Week 4 - Execution engine**: bracket-like two-leg spread entry/exit, partial-fill recovery, slippage controls, market-depth checks.
5. **Week 5 - Scheduler/calendar**: NSE holiday calendar, entry windows, force square-off, heartbeat, deployment runbook.
6. **Week 6+ - Validation**: backtests, paper trading reports, chaos testing for network/API errors, small-size supervised live rollout.
