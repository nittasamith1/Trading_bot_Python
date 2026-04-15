# Binance Futures Testnet Trading Bot

A command-line trading bot for placing orders on Binance Futures Testnet (USDT-M).
Supports **MARKET**, **LIMIT**, and **STOP_MARKET** orders with structured logging,
clean error handling, and a layered codebase.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST client (signing, transport, error parsing)
│   ├── orders.py          # Order placement logic (market, limit, stop-market)
│   ├── validators.py      # Input validation — raises ValueError with clear messages
│   └── logging_config.py  # Dual-output logging (console WARNING+, file DEBUG+)
├── logs/
│   └── trading_bot.log    # Auto-created on first run
├── cli.py                 # Argparse CLI entry point
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Binance Futures Testnet account

1. Go to <https://testnet.binancefuture.com> and register / log in.
2. Under **API Management**, generate a new API key and secret.
3. Make a note of both values — the secret is shown **only once**.

### 2. Python environment

```bash
# Requires Python 3.8+
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Credentials

Export your testnet keys as environment variables (recommended):

```bash
export BINANCE_API_KEY="your_testnet_api_key"
export BINANCE_API_SECRET="your_testnet_api_secret"
```

Or pass them directly with `--api-key` / `--api-secret` flags (less secure).

---

## How to Run

All commands are run from inside the `trading_bot/` directory.

### Market order — BUY

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type MARKET \
  --quantity 0.001
```

### Market order — SELL

```bash
python cli.py \
  --symbol BTCUSDT \
  --side SELL \
  --type MARKET \
  --quantity 0.001
```

### Limit order — BUY

```bash
python cli.py \
  --symbol ETHUSDT \
  --side BUY \
  --type LIMIT \
  --quantity 0.01 \
  --price 2500
```

### Limit order — SELL

```bash
python cli.py \
  --symbol ETHUSDT \
  --side SELL \
  --type LIMIT \
  --quantity 0.01 \
  --price 3200 \
  --tif GTC
```

### Stop-Market order — BUY (bonus order type)

Triggers a market buy when the mark price crosses `--stop-price`.

```bash
python cli.py \
  --symbol BTCUSDT \
  --side BUY \
  --type STOP_MARKET \
  --quantity 0.001 \
  --stop-price 95000
```

### Dry run (validate only, no order placed)

```bash
python cli.py \
  --symbol BTCUSDT --side BUY --type LIMIT \
  --quantity 0.001 --price 90000 \
  --dry-run
```

---

## Output

### Successful market order

```
  ╔════════════════════════════════════════╗
  ║   Binance Futures Testnet Trading Bot  ║
  ╚════════════════════════════════════════╝

── Order Request Summary ─────────────────────────
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Quantity      : 0.001
──────────────────────────────────────────────────

── Order Response ────────────────────────────────
────────────────────────────────────────────────
  Order ID      : 3428791234
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Status        : FILLED
  Orig Qty      : 0.001
  Executed Qty  : 0.001
  Avg Price     : 94312.50
────────────────────────────────────────────────
  ✓ Order placed successfully!
```

---

## Logging

Log files are written to `logs/trading_bot.log` and rotate at 5 MB (3 backups kept).

| Destination | Level   | Purpose                                    |
|-------------|---------|---------------------------------------------|
| File        | DEBUG   | Full request params, raw API responses       |
| Console     | WARNING | Errors / warnings only (clean terminal UX)  |

To increase console verbosity during debugging:

```bash
python cli.py ... --log-level DEBUG
```

---

## Assumptions

- **Testnet only** — the base URL is hard-coded to `https://testnet.binancefuture.com`.
  Do **not** use real credentials with this bot without updating the URL.
- **USDT-M perpetuals** — all pairs should end in `USDT` (e.g. `BTCUSDT`, `ETHUSDT`).
- **No position-mode check** — the bot does not adjust hedge/one-way mode automatically.
  Binance Testnet defaults to *One-Way* mode; this bot is designed for that setting.
- Quantity and price precision are passed as provided; Binance returns an error if they
  exceed the symbol's allowed precision (check `GET /fapi/v1/exchangeInfo`).

---

## Error handling

| Scenario               | Behaviour                                              |
|------------------------|--------------------------------------------------------|
| Invalid CLI input      | Prints validation error, exits with code 1             |
| Missing credentials    | Prints clear message, exits with code 1                |
| Binance API error      | Prints error code + message, logs full details to file |
| Network failure        | Prints network error, logs traceback to file           |
| Unexpected exception   | Prints error, logs full traceback to file              |
