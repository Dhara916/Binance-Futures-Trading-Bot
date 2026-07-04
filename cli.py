#!/usr/bin/env python3
"""
cli.py

Command-line entry point for the Binance Futures Testnet trading bot.

Usage:
    # Non-interactive (scriptable)
    python cli.py market --symbol BTCUSDT --side BUY --quantity 0.01
    python cli.py limit  --symbol BTCUSDT --side SELL --quantity 0.01 --price 50000

    # Guided, prompt-based mode (bonus: enhanced CLI UX)
    python cli.py interactive
    python cli.py                 # no args also drops into interactive mode

    # Test the whole pipeline without hitting the network / needing keys
    python cli.py market --symbol BTCUSDT --side BUY --quantity 0.01 --dry-run
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Optional

# colorama makes ANSI colors work in older Windows terminals (cmd.exe).
# It's optional — if it's not installed, colors simply won't render there.
try:
    import colorama

    colorama.init()
except ImportError:  # pragma: no cover
    pass

from bot.client import BinanceFuturesClient, BinanceFuturesClientError
from bot.logging_config import setup_logging
from bot.orders import OrderResult, place_order
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


# --------------------------------------------------------------------------
# Small terminal-color helper (no hard dependency required)
# --------------------------------------------------------------------------
class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def wrap(cls, text: str, color: str) -> str:
        if not sys.stdout.isatty():
            return text
        return f"{color}{text}{cls.RESET}"


def _print_banner() -> None:
    print(Color.wrap("=" * 56, Color.CYAN))
    print(Color.wrap("  Binance Futures Testnet - Simplified Trading Bot", Color.BOLD))
    print(Color.wrap("=" * 56, Color.CYAN))


def _print_request_summary(request: dict) -> None:
    print(Color.wrap("\nOrder request:", Color.YELLOW))
    for key in ("symbol", "side", "type", "quantity", "price", "timeInForce"):
        if key in request:
            print(f"  {key:<14}: {request[key]}")


def _print_response(result: OrderResult) -> None:
    if result.success:
        r = result.response or {}
        print(Color.wrap("\nOrder response:", Color.YELLOW))
        print(f"  orderId       : {r.get('orderId')}")
        print(f"  status        : {r.get('status')}")
        print(f"  executedQty   : {r.get('executedQty')}")
        print(f"  avgPrice      : {r.get('avgPrice', 'N/A')}")
        print(Color.wrap("\n[OK] Order placed successfully.\n", Color.GREEN + Color.BOLD))
    else:
        print(Color.wrap(f"\n[FAILED] Order failed: {result.error}\n", Color.RED + Color.BOLD))


def _build_client(args: argparse.Namespace) -> Optional[BinanceFuturesClient]:
    try:
        return BinanceFuturesClient(
            api_key=args.api_key,
            api_secret=args.api_secret,
            dry_run=args.dry_run,
        )
    except BinanceFuturesClientError as exc:
        print(Color.wrap(f"\n[FAILED] Setup error: {exc}\n", Color.RED + Color.BOLD))
        return None


def _run_order(args: argparse.Namespace, order_type: str) -> int:
    client = _build_client(args)
    if client is None:
        return 1

    result = place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=order_type,
        quantity=args.quantity,
        price=getattr(args, "price", None),
        time_in_force=getattr(args, "time_in_force", "GTC"),
    )

    if result.request:
        _print_request_summary(result.request)
    _print_response(result)
    return 0 if result.success else 1


# --------------------------------------------------------------------------
# Interactive mode (bonus: enhanced CLI UX)
# --------------------------------------------------------------------------
def _prompt(label: str, validator, *, default: Optional[str] = None) -> str:
    """Repeatedly prompts until `validator` accepts the input, printing a
    friendly, specific error message and looping instead of crashing."""
    suffix = f" [{default}]" if default else ""
    while True:
        raw = input(Color.wrap(f"{label}{suffix}: ", Color.CYAN)).strip()
        if not raw and default is not None:
            raw = default
        try:
            return validator(raw)
        except ValidationError as exc:
            print(Color.wrap(f"  x {exc}", Color.RED))


def run_interactive(args: argparse.Namespace) -> int:
    _print_banner()
    print(Color.wrap("\nGuided order entry - press Ctrl+C at any time to cancel.\n", Color.DIM))

    client = _build_client(args)
    if client is None:
        return 1

    try:
        symbol = _prompt("Symbol (e.g. BTCUSDT)", validate_symbol)
        side = _prompt("Side (BUY/SELL)", validate_side)
        order_type = _prompt("Order type (MARKET/LIMIT)", validate_order_type)
        quantity = _prompt("Quantity", validate_quantity)

        price = None
        if order_type == "LIMIT":
            price = _prompt("Price", lambda v: validate_price(v, "LIMIT"))

        print()
        confirm_line = f"Confirm: {side} {order_type} {quantity} {symbol}"
        if price:
            confirm_line += f" @ {price}"
        confirm = input(Color.wrap(confirm_line + "  (y/n): ", Color.YELLOW)).strip().lower()

        if confirm not in ("y", "yes"):
            print(Color.wrap("\nCancelled.\n", Color.DIM))
            return 0

        result = place_order(
            client=client,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
        )
        if result.request:
            _print_request_summary(result.request)
        _print_response(result)
        return 0 if result.success else 1

    except KeyboardInterrupt:
        print(Color.wrap("\n\nCancelled by user.\n", Color.DIM))
        return 130


# --------------------------------------------------------------------------
# Argument parsing
# --------------------------------------------------------------------------
def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", default=None, help="Binance Testnet API key (or set BINANCE_API_KEY)")
    parser.add_argument("--api-secret", default=None, help="Binance Testnet API secret (or set BINANCE_API_SECRET)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the order locally without calling the Binance API (no credentials needed).",
    )
    parser.add_argument("--verbose", action="store_true", help="Also print debug-level logs to the console.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET or LIMIT orders on Binance Futures Testnet (USDT-M).",
    )
    subparsers = parser.add_subparsers(dest="command")

    market_parser = subparsers.add_parser("market", help="Place a MARKET order")
    market_parser.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    market_parser.add_argument("--side", required=True, help="BUY or SELL")
    market_parser.add_argument("--quantity", required=True, help="Order quantity")
    _add_common_args(market_parser)
    market_parser.set_defaults(func=lambda args: _run_order(args, "MARKET"))

    limit_parser = subparsers.add_parser("limit", help="Place a LIMIT order")
    limit_parser.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    limit_parser.add_argument("--side", required=True, help="BUY or SELL")
    limit_parser.add_argument("--quantity", required=True, help="Order quantity")
    limit_parser.add_argument("--price", required=True, help="Limit price")
    limit_parser.add_argument("--time-in-force", default="GTC", help="GTC / IOC / FOK (default: GTC)")
    _add_common_args(limit_parser)
    limit_parser.set_defaults(func=lambda args: _run_order(args, "LIMIT"))

    interactive_parser = subparsers.add_parser("interactive", help="Guided, prompt-based order entry")
    _add_common_args(interactive_parser)
    interactive_parser.set_defaults(func=run_interactive)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    raw_args = sys.argv[1:] if argv is None else argv
    parser = build_parser()

    # No arguments at all -> friendliest default is the guided flow.
    args = parser.parse_args(["interactive"] if not raw_args else raw_args)

    setup_logging(verbose=getattr(args, "verbose", False))

    if args.command != "interactive":
        _print_banner()

    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 - top-level safety net
        print(Color.wrap(f"\n[FAILED] Unexpected error: {exc}\n", Color.RED + Color.BOLD))
        return 1


if __name__ == "__main__":
    sys.exit(main())
