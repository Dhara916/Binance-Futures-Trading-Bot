# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI application for placing MARKET and LIMIT
orders on Binance Futures Testnet, with clean separation between the API
layer and the command layer, structured logging, input validation, and an
enhanced interactive CLI mode.

## Project structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance Futures Testnet client wrapper (API layer)
    orders.py           # order-building / placement logic
    validators.py       # input validation, independent of network/CLI
    logging_config.py   # rotating file + console logging setup
  cli.py                # CLI entry point (argparse + interactive mode)
  logs/
    trading_bot.log     # generated at runtime — full request/response/error log
  README.md
  requirements.txt
```

**Why this split:** `client.py` only knows how to talk to Binance. `orders.py`
only knows how to turn validated input into a request and interpret the
result. `validators.py` has no side effects, so it's trivial to unit test.
`cli.py` is the only file that knows about argparse, prompts, or terminal
colors — it owns *presentation*, not business logic.

## Setup

### 1. Binance Futures Testnet account

1. Go to https://testnet.binancefuture.com and register/log in (you can use
   a GitHub account).
2. Once logged in, go to **API Key** management and generate a testnet API
   key + secret.
3. The testnet gives you a virtual USDT balance automatically — no real
   funds are involved anywhere in this project.

### 2. Install

Requires Python 3.9+ (tested on 3.12; also works on 3.10–3.13).

```bash
git clone <your-repo-url>
cd trading_bot
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure credentials

Set your testnet API key/secret as environment variables (preferred — keeps
secrets out of shell history and `argparse --help` output):

```bash
# Windows (PowerShell)
$env:BINANCE_API_KEY="your_testnet_key"
$env:BINANCE_API_SECRET="your_testnet_secret"

# macOS / Linux
export BINANCE_API_KEY="your_testnet_key"
export BINANCE_API_SECRET="your_testnet_secret"
```

Alternatively, pass `--api-key` / `--api-secret` directly on the command
line for a one-off run.

## How to run

### Non-interactive (scriptable)

```bash
# MARKET order
python cli.py market --symbol BTCUSDT --side BUY --quantity 0.01

# LIMIT order
python cli.py limit --symbol BTCUSDT --side SELL --quantity 0.01 --price 68000

# LIMIT order with an explicit time-in-force
python cli.py limit --symbol ETHUSDT --side BUY --quantity 0.5 --price 3200 --time-in-force IOC
```

### Interactive / guided mode (bonus: enhanced CLI UX)

```bash
python cli.py interactive
# or just:
python cli.py
```

This walks you through symbol → side → order type → quantity → (price, if
LIMIT) → confirmation, re-prompting with a specific error message whenever
input is invalid, and asking for a final `y/n` confirmation before sending
the order.

### Dry-run mode (no API keys needed)

Every subcommand accepts `--dry-run`, which skips the credentials check
entirely and returns a locally-simulated (but realistically shaped)
response instead of calling Binance. This is the fastest way to try the
tool out, test the CLI/logging pipeline, or demo it before you've generated
testnet API keys:

```bash
python cli.py market --symbol BTCUSDT --side BUY --quantity 0.01 --dry-run --verbose
python cli.py limit --symbol BTCUSDT --side SELL --quantity 0.01 --price 68000 --dry-run --verbose
python cli.py interactive --dry-run
```

It still runs the full pipeline — validation, request building, logging to
`logs/trading_bot.log`, and printing the request summary / response /
success-failure message — it just fakes the Binance response instead of
making a real HTTP call.

**Note:** the log entries you submit as deliverables should come from real
testnet API calls (i.e. without `--dry-run`), so that `orderId`/`avgPrice`
reflect genuine responses from Binance. Use `--dry-run` to sanity-check the
tool, then rerun the same commands with real credentials for your final
submission logs.

### Output

Every run prints:
- an **order request summary** (symbol, side, type, quantity, price if
  applicable)
- the **order response** (`orderId`, `status`, `executedQty`, `avgPrice`)
- a clear **success/failure message**

### Logs

All requests, responses, and errors are logged to `logs/trading_bot.log`
(rotating, 2 MB per file, 5 backups kept). Console output is quiet by
default; pass `--verbose` to also see log lines in the terminal.

The `logs/trading_bot.log` file included in this submission contains one
MARKET order and one LIMIT order run with `--dry-run` (see Assumptions
below for why), plus an example of a validation error being logged.

## Assumptions

- **The `logs/trading_bot.log` file included in this submission was
  generated with `--dry-run`**, since it was produced before real testnet
  API keys were available. `--dry-run` exercises the exact same
  validation → request-building → logging → response-printing pipeline as
  a real call, minus the actual HTTP request, so the log format is
  identical to a genuine run. Running the same commands with real testnet
  credentials (without `--dry-run`) produces logs in the same format,
  sourced from Binance's actual API response — do this to generate your
  own final submission logs.
- Only `symbol`, `side`, `type`, `quantity`, `price` (LIMIT only), and
  `timeInForce` (LIMIT only, default `GTC`) are sent — no leverage/margin
  type switching, position-side, or reduce-only flags are set, since these
  aren't part of the stated requirements. Binance will use your account's
  existing testnet defaults for those.
- Symbols are validated with a simple format check (5–20 uppercase
  alphanumeric characters, e.g. `BTCUSDT`) rather than a live lookup against
  Binance's exchange-info endpoint, to keep the tool usable offline/in
  `--dry-run` mode. An invalid-but-correctly-formatted symbol will still be
  rejected by Binance itself, and that rejection is caught, logged, and
  shown to the user like any other API error.
- `quantity` and `price` are validated as "a positive number" — Binance's
  own per-symbol precision/step-size (`LOT_SIZE`) rules are enforced
  server-side; a violation surfaces as a normal API error in the response.

## Troubleshooting (Windows-specific)

- If `pip install` fails to build a dependency on Python 3.13/3.14, this is
  usually a package not yet publishing wheels for that Python version.
  `python-binance` itself is pure Python and has no compiled dependencies,
  so this is unlikely to affect this project directly — but if you hit it
  elsewhere in your environment, using Python 3.11 or 3.12 in your venv is
  the most reliable fix.
- If colors don't render in `cmd.exe`, make sure `colorama` installed
  successfully (`pip show colorama`) — it's what translates ANSI codes for
  older Windows terminals. Windows Terminal / PowerShell 7 support ANSI
  natively either way.

## Bonus implemented

**Enhanced CLI UX** — `python cli.py interactive` (or running with no
arguments) provides a guided, step-by-step prompt flow with:
- inline validation and specific, actionable error messages (re-prompts
  instead of crashing)
- a final human-readable confirmation step before any order is sent
- colorized success/failure/warning output (auto-disabled when output
  isn't a terminal, e.g. when piped to a file)
