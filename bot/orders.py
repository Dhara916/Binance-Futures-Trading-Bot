"""
bot/orders.py

Business logic for shaping and placing orders. Sits between the CLI layer
(cli.py) and the low-level API wrapper (client.py). Nothing here talks to
argparse or the network directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import BinanceFuturesClient, BinanceFuturesClientError
from .validators import ValidationError, validate_order_params

logger = logging.getLogger("trading_bot")


@dataclass
class OrderResult:
    """Structured result returned to the CLI layer. Never raises — the CLI
    decides how to present success/failure to the user."""

    success: bool
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """Validates raw CLI/prompt input and turns it into a Binance-ready params dict."""
    clean = validate_order_params(symbol, side, order_type, quantity, price)

    params: Dict[str, Any] = {
        "symbol": clean["symbol"],
        "side": clean["side"],
        "type": clean["order_type"],
        "quantity": clean["quantity"],
    }

    if clean["order_type"] == "LIMIT":
        params["price"] = clean["price"]
        params["timeInForce"] = time_in_force

    return params


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Validates input, submits the order via `client`, and returns a
    structured OrderResult. Handles both validation errors (bad input)
    and client errors (API rejection / network failure) without raising.
    """
    try:
        request = build_order_request(symbol, side, order_type, quantity, price, time_in_force)
    except ValidationError as exc:
        logger.warning("Validation failed for order input: %s", exc)
        return OrderResult(success=False, request={}, error=str(exc))

    try:
        response = client.place_order(**request)
        return OrderResult(success=True, request=request, response=response)
    except BinanceFuturesClientError as exc:
        logger.error("Order placement failed: %s", exc)
        return OrderResult(success=False, request=request, error=str(exc))
