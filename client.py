"""
Order placement logic.

Translates validated user inputs into Binance API parameters and delegates
the actual HTTP call to BinanceClient.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceClient
from .logging_config import get_logger

logger = get_logger("orders")


class OrderResult:
    """Structured representation of a placed order response."""

    def __init__(self, raw: Dict[str, Any]) -> None:
        self.raw = raw
        self.order_id: int = raw.get("orderId", 0)
        self.client_order_id: str = raw.get("clientOrderId", "")
        self.symbol: str = raw.get("symbol", "")
        self.status: str = raw.get("status", "")
        self.side: str = raw.get("side", "")
        self.order_type: str = raw.get("type", "")
        self.orig_qty: str = raw.get("origQty", "")
        self.executed_qty: str = raw.get("executedQty", "")
        self.avg_price: str = raw.get("avgPrice", "")
        self.price: str = raw.get("price", "")
        self.time_in_force: str = raw.get("timeInForce", "")
        self.update_time: int = raw.get("updateTime", 0)

    def __str__(self) -> str:
        lines = [
            "─" * 48,
            f"  Order ID      : {self.order_id}",
            f"  Symbol        : {self.symbol}",
            f"  Side          : {self.side}",
            f"  Type          : {self.order_type}",
            f"  Status        : {self.status}",
            f"  Orig Qty      : {self.orig_qty}",
            f"  Executed Qty  : {self.executed_qty}",
        ]
        if self.avg_price and self.avg_price != "0":
            lines.append(f"  Avg Price     : {self.avg_price}")
        if self.price and self.price != "0":
            lines.append(f"  Limit Price   : {self.price}")
        if self.time_in_force:
            lines.append(f"  Time in Force : {self.time_in_force}")
        lines.append("─" * 48)
        return "\n".join(lines)


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
) -> OrderResult:
    """Place a MARKET order."""
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": str(quantity),
    }
    logger.info("Building MARKET order | %s %s qty=%s", side, symbol, quantity)
    raw = client.place_order(params)
    return OrderResult(raw)


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
) -> OrderResult:
    """Place a LIMIT order."""
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": str(quantity),
        "price": str(price),
        "timeInForce": time_in_force,
    }
    logger.info(
        "Building LIMIT order | %s %s qty=%s price=%s tif=%s",
        side, symbol, quantity, price, time_in_force,
    )
    raw = client.place_order(params)
    return OrderResult(raw)


def place_stop_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    stop_price: Decimal,
) -> OrderResult:
    """Place a STOP_MARKET order (bonus order type)."""
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": "STOP_MARKET",
        "quantity": str(quantity),
        "stopPrice": str(stop_price),
    }
    logger.info(
        "Building STOP_MARKET order | %s %s qty=%s stopPrice=%s",
        side, symbol, quantity, stop_price,
    )
    raw = client.place_order(params)
    return OrderResult(raw)
