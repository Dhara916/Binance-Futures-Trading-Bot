"""
bot/validators.py

Pure input-validation functions — no network calls, no logging side effects.
Kept separate from client.py/orders.py so they're trivial to unit test and
so the same rules can be reused by both the argparse CLI and the
interactive prompt flow.
"""
from __future__ import annotations

import re
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}
# Futures symbols are uppercase alphanumerics, typically BASE+QUOTE, e.g. BTCUSDT
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(Exception):
    """Raised when user-supplied order parameters fail validation."""


def validate_symbol(symbol: str) -> str:
    symbol = (symbol or "").strip().upper()
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")
    if not SYMBOL_PATTERN.match(symbol):
        raise ValidationError(
            f"'{symbol}' doesn't look like a valid futures symbol (e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    side = (side or "").strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Side must be one of {sorted(VALID_SIDES)}, got '{side}'.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = (order_type or "").strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0.")
    return quantity


def validate_price(price, order_type: str) -> Optional[float]:
    if order_type == "LIMIT":
        if price is None or price == "":
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            price = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Price must be a number, got '{price}'.")
        if price <= 0:
            raise ValidationError("Price must be greater than 0.")
        return price
    # MARKET orders ignore price entirely, even if one was supplied.
    return None


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity,
    price=None,
) -> dict:
    """Runs all validators and returns a clean, normalised dict of params."""
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_quantity = validate_quantity(quantity)
    clean_price = validate_price(price, clean_type)

    return {
        "symbol": clean_symbol,
        "side": clean_side,
        "order_type": clean_type,
        "quantity": clean_quantity,
        "price": clean_price,
    }
