#!/usr/bin/env python3
"""
cli.py — Command-line entry point for the Binance Futures Testnet trading bot.

Usage examples
--------------
# Market BUY
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Limit SELL
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 2800

# Stop-Market BUY (bonus order type)
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000

Environment variables
---------------------
BINANCE_API_KEY    — testnet API key
BINANCE_API_SECRET — testnet API secret

Alternatively pass --api-key / --api-secret directly (not recommended for production).
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from decimal import Decimal

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import setup_logging
from bot.orders import place_limit_order, place_market_order, place_stop_market_order
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

# ── Banner ─────────────────────────────────────────────────────────────────────

BANNER = r"""
  ╔════════════════════════════════════════╗
  ║   Binance Futures Testnet Trading Bot  ║
  ╚════════════════════════════════════════╝
"""


# ── Argument parser ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=textwrap.dedent("""\
            Place orders on Binance Futures Testnet (USDT-M).

            API credentials are read from the environment variables
            BINANCE_API_KEY and BINANCE_API_SECRET, or passed via flags.
        """),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Market buy
              python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

              # Limit sell
              python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 2800

              # Stop-Market buy
              python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 95000
        """),
    )

    # Credentials (optional — prefer env vars)
    creds = parser.add_argument_group("API credentials (prefer env vars)")
    creds.add_argument(
        "--api-key",
        default=os.environ.get("BINANCE_API_KEY"),
        help="Binance Testnet API key (or set BINANCE_API_KEY env var)",
    )
    creds.add_argument(
        "--api-secret",
        default=os.environ.get("BINANCE_API_SECRET"),
        help="Binance Testnet API secret (or set BINANCE_API_SECRET env var)",
    )

    # Order parameters
    order = parser.add_argument_group("Order parameters")
    order.add_argument("--symbol",   required=True, help="Trading pair, e.g. BTCUSDT")
    order.add_argument("--side",     required=True, help="BUY or SELL")
    order.add_argument("--type",     required=True, dest="order_type",
                       help="MARKET, LIMIT, or STOP_MARKET")
    order.add_argument("--quantity", required=True, help="Order quantity")
    order.add_argument("--price",    default=None,
                       help="Limit price (required for LIMIT orders)")
    order.add_argument("--stop-price", dest="stop_price", default=None,
                       help="Stop trigger price (required for STOP_MARKET orders)")
    order.add_argument("--tif",      default="GTC",
                       help="Time-in-force for LIMIT orders (default: GTC)")

    # Misc
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity (default: INFO)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate inputs and print summary without placing the order")

    return parser


# ── Helpers ────────────────────────────────────────────────────────────────────

def _print_request_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Decimal | None,
    stop_price: Decimal | None,
    tif: str,
) -> None:
    print("\n── Order Request Summary ─────────────────────────")
    print(f"  Symbol        : {symbol}")
    print(f"  Side          : {side}")
    print(f"  Type          : {order_type}")
    print(f"  Quantity      : {quantity}")
    if price is not None:
        print(f"  Price         : {price}")
        print(f"  Time in Force : {tif}")
    if stop_price is not None:
        print(f"  Stop Price    : {stop_price}")
    print("──────────────────────────────────────────────────\n")


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Initialise logging first so everything below is captured
    logger = setup_logging(args.log_level)
    logger.info("=== Trading Bot Session Start ===")

    print(BANNER)

    # ── Validate inputs ───────────────────────────────────────────────────────
    try:
        symbol     = validate_symbol(args.symbol)
        side       = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity   = validate_quantity(args.quantity)
        price      = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValueError as exc:
        print(f"\n✗ Validation error: {exc}\n", file=sys.stderr)
        logger.error("Validation error: %s", exc)
        return 1

    _print_request_summary(symbol, side, order_type, quantity, price, stop_price, args.tif)

    # ── Dry-run short-circuit ─────────────────────────────────────────────────
    if args.dry_run:
        print("  [DRY RUN] Order NOT placed. Remove --dry-run to execute.\n")
        logger.info("Dry-run mode — order not placed.")
        return 0

    # ── Credentials check ─────────────────────────────────────────────────────
    if not args.api_key or not args.api_secret:
        print(
            "✗ API credentials are missing.\n"
            "  Set BINANCE_API_KEY and BINANCE_API_SECRET env vars, "
            "or pass --api-key / --api-secret.\n",
            file=sys.stderr,
        )
        logger.error("Missing API credentials.")
        return 1

    # ── Instantiate client ────────────────────────────────────────────────────
    try:
        client = BinanceClient(api_key=args.api_key, api_secret=args.api_secret)
    except ValueError as exc:
        print(f"✗ Client initialisation error: {exc}\n", file=sys.stderr)
        logger.error("Client init error: %s", exc)
        return 1

    # ── Place order ───────────────────────────────────────────────────────────
    try:
        if order_type == "MARKET":
            result = place_market_order(client, symbol, side, quantity)
        elif order_type == "LIMIT":
            result = place_limit_order(client, symbol, side, quantity, price, args.tif)
        elif order_type == "STOP_MARKET":
            result = place_stop_market_order(client, symbol, side, quantity, stop_price)
        else:
            # Should never reach here after validation, but be defensive
            raise ValueError(f"Unsupported order type: {order_type}")

    except BinanceAPIError as exc:
        print(f"\n✗ API error [{exc.code}]: {exc.message}\n", file=sys.stderr)
        logger.error("API error placing order: %s", exc)
        return 1
    except ConnectionError as exc:
        print(f"\n✗ Network error: {exc}\n", file=sys.stderr)
        logger.error("Network error: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\n✗ Unexpected error: {exc}\n", file=sys.stderr)
        logger.exception("Unexpected error: %s", exc)
        return 1

    # ── Print result ──────────────────────────────────────────────────────────
    print("── Order Response ────────────────────────────────")
    print(result)
    print(f"  ✓ Order placed successfully!\n")
    logger.info("=== Trading Bot Session End (success) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
