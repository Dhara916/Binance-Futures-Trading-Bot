"""
bot/client.py

Thin wrapper around python-binance's Client, configured to talk to the
Binance USDT-M Futures Testnet (https://testnet.binancefuture.com).

This module owns:
  - authentication / connection setup
  - sending raw order requests
  - translating low-level SDK/network exceptions into a single
    BinanceFuturesClientError so callers only need to catch one thing

Order-shaping / business logic lives in orders.py, not here.
"""
from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Dict, Optional

from binance import Client
from binance.exceptions import (
    BinanceAPIException,
    BinanceOrderException,
    BinanceRequestException,
)

logger = logging.getLogger("trading_bot")

FUTURES_TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceFuturesClientError(Exception):
    """Raised for any error originating from the Binance Futures client wrapper."""


class BinanceFuturesClient:
    """
    Wraps python-binance's Client to talk to Binance USDT-M Futures Testnet.

    Set dry_run=True to simulate order responses locally without any
    network access or API credentials — useful for testing the CLI/logging
    pipeline end to end.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        dry_run: bool = False,
    ) -> None:
        self.dry_run = dry_run
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")

        if not self.dry_run and (not self.api_key or not self.api_secret):
            raise BinanceFuturesClientError(
                "Missing API credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET "
                "environment variables (or pass --api-key/--api-secret), or use "
                "--dry-run to test without them."
            )

        self._client: Optional[Client] = None
        if not self.dry_run:
            self._client = self._build_client()

    def _build_client(self) -> Client:
        try:
            client = Client(self.api_key, self.api_secret, testnet=True)
            # Explicitly pin the futures base URL to the testnet. This is a
            # defensive belt-and-braces step in case the installed
            # python-binance version doesn't map testnet=True onto the
            # futures endpoint (it has historically only affected spot).
            client.FUTURES_URL = f"{FUTURES_TESTNET_BASE_URL}/fapi"
            logger.debug(
                "Binance Futures client initialised for testnet at %s",
                FUTURES_TESTNET_BASE_URL,
            )
            return client
        except Exception as exc:  # noqa: BLE001 - wrap anything the SDK raises
            logger.exception("Failed to initialise Binance client")
            raise BinanceFuturesClientError(f"Could not initialise Binance client: {exc}") from exc

    def place_order(self, **params: Any) -> Dict[str, Any]:
        """
        Sends a futures order request. `params` should match the Binance
        Futures 'New Order' endpoint fields, e.g.:
            symbol, side, type, quantity, price, timeInForce, ...
        """
        logger.info("Sending order request: %s", params)

        if self.dry_run:
            response = self._simulate_response(params)
            logger.info("[DRY-RUN] Simulated order response: %s", response)
            return response

        try:
            response = self._client.futures_create_order(**params)
            logger.info("Order response received: %s", response)
            return response
        except (BinanceAPIException, BinanceOrderException) as exc:
            logger.error("Binance API rejected the order: %s", exc)
            raise BinanceFuturesClientError(f"Binance API error: {exc}") from exc
        except BinanceRequestException as exc:
            logger.error("Malformed request sent to Binance: %s", exc)
            raise BinanceFuturesClientError(f"Request error: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - network errors, timeouts, DNS, etc.
            logger.exception("Network or unexpected error while placing order")
            raise BinanceFuturesClientError(f"Network/unexpected error: {exc}") from exc

    @staticmethod
    def _simulate_response(params: Dict[str, Any]) -> Dict[str, Any]:
        """Builds a fake-but-realistic response for --dry-run mode."""
        qty = float(params.get("quantity", 0))
        price = float(params.get("price", 0)) if params.get("price") else 0.0
        is_market = params.get("type") == "MARKET"

        return {
            "orderId": random.randint(10_000_000, 99_999_999),
            "symbol": params.get("symbol"),
            "status": "FILLED" if is_market else "NEW",
            "clientOrderId": f"dryrun_{int(time.time())}",
            "price": f"{price:.2f}",
            "avgPrice": f"{price:.2f}" if is_market else "0.00",
            "origQty": f"{qty}",
            "executedQty": f"{qty}" if is_market else "0",
            "side": params.get("side"),
            "type": params.get("type"),
            "timeInForce": params.get("timeInForce", "GTC"),
            "updateTime": int(time.time() * 1000),
        }
