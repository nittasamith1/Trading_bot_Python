"""
Binance Futures Testnet REST client.

Handles:
  - HMAC-SHA256 request signing
  - Timestamping
  - HTTP error parsing
  - Structured logging of every request and response
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

BASE_URL = "https://testnet.binancefuture.com"
_RECV_WINDOW = 5000  # milliseconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx status or an error payload."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class BinanceClient:
    """Thin wrapper around the Binance Futures Testnet REST API."""

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")
        self._api_key = api_key
        self._api_secret = api_secret.encode()
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.debug("BinanceClient initialised (base_url=%s)", BASE_URL)

    # ──────────────────────────────────────────────────────────────────────────
    # Public helpers
    # ──────────────────────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if the testnet endpoint is reachable."""
        try:
            self._get("/fapi/v1/ping", signed=False)
            logger.info("Ping successful — testnet is reachable.")
            return True
        except Exception as exc:
            logger.warning("Ping failed: %s", exc)
            return False

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange information (symbol filters, precision, etc.)."""
        return self._get("/fapi/v1/exchangeInfo", signed=False)

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch account balance and position information."""
        return self._get("/fapi/v2/account", signed=True)

    def place_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place a new order on Binance Futures Testnet.

        Parameters are validated upstream; this method only handles transport.
        """
        logger.info(
            "Placing order | symbol=%s side=%s type=%s qty=%s price=%s",
            params.get("symbol"),
            params.get("side"),
            params.get("type"),
            params.get("quantity"),
            params.get("price", "N/A"),
        )
        response = self._post("/fapi/v1/order", params=params, signed=True)
        logger.info(
            "Order placed   | orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice", "N/A"),
        )
        return response

    # ──────────────────────────────────────────────────────────────────────────
    # Private transport layer
    # ──────────────────────────────────────────────────────────────────────────

    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self._api_secret,
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _add_auth(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = _RECV_WINDOW
        query_string = urlencode(params)
        params["signature"] = self._sign(query_string)
        return params

    def _get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        params = params or {}
        if signed:
            params = self._add_auth(params)
        url = BASE_URL + path
        logger.debug("GET %s | params=%s", url, self._redact(params))
        resp = self._session.get(url, params=params, timeout=self._timeout)
        return self._handle_response(resp)

    def _post(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        params = params or {}
        if signed:
            params = self._add_auth(params)
        url = BASE_URL + path
        logger.debug("POST %s | body=%s", url, self._redact(params))
        resp = self._session.post(url, data=params, timeout=self._timeout)
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: requests.Response) -> Dict[str, Any]:
        logger.debug(
            "Response | status=%s body=%s",
            resp.status_code,
            resp.text[:500],  # cap log size
        )
        try:
            data = resp.json()
        except ValueError:
            raise BinanceAPIError(resp.status_code, f"Non-JSON response: {resp.text[:200]}")

        if not resp.ok or isinstance(data, dict) and "code" in data and data["code"] != 200:
            code = data.get("code", resp.status_code)
            msg = data.get("msg", resp.text)
            logger.error("API error | code=%s msg=%s", code, msg)
            raise BinanceAPIError(code, msg)

        return data

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of params with sensitive fields masked for logging."""
        redacted = dict(params)
        for key in ("signature",):
            if key in redacted:
                redacted[key] = "***"
        return redacted
