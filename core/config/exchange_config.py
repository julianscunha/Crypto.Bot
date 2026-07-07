# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

# =====================================================
# HELPERS
# =====================================================

def positive_float(
    value,
    fallback
):

    try:

        value = float(value)

        if value <= 0:

            return fallback

        return value

    except Exception:

        return fallback


def non_negative_float(
    value,
    fallback
):

    try:

        value = float(value)

        if value < 0:

            return fallback

        return value

    except Exception:

        return fallback


def positive_int(
    value,
    fallback
):

    try:

        value = int(value)

        if value <= 0:

            return fallback

        return value

    except Exception:

        return fallback


def boolean(
    value,
    fallback
):

    if isinstance(
        value,
        bool
    ):

        return value

    if value is None:

        return fallback

    return str(value).strip().lower() in [

        "1",

        "true",

        "yes",

        "on"
    ]

# =====================================================
# EXCHANGE CONFIG
# =====================================================

EXCHANGE_CONFIG = {

    # =================================================
    # FEES
    # =================================================

    "enable_fee_simulation":

        boolean(

            getattr(
                settings,
                "ENABLE_FEE_SIMULATION",
                True
            ),

            True
        ),

    "maker_fee_percent":

        non_negative_float(

            getattr(
                settings,
                "MAKER_FEE_PERCENT",
                0.001
            ),

            0.001
        ),

    "taker_fee_percent":

        non_negative_float(

            getattr(
                settings,
                "TAKER_FEE_PERCENT",
                0.001
            ),

            0.001
        ),

    # =================================================
    # SLIPPAGE
    # =================================================

    "enable_slippage_simulation":

        boolean(

            getattr(
                settings,
                "ENABLE_SLIPPAGE_SIMULATION",
                True
            ),

            True
        ),

    "entry_slippage_percent":

        non_negative_float(

            getattr(
                settings,
                "ENTRY_SLIPPAGE_PERCENT",
                0.0002
            ),

            0.0002
        ),

    "exit_slippage_percent":

        non_negative_float(

            getattr(
                settings,
                "EXIT_SLIPPAGE_PERCENT",
                0.0002
            ),

            0.0002
        ),

    # =================================================
    # PRICE PRECISION
    # =================================================

    "price_precision":

        positive_int(

            getattr(
                settings,
                "PRICE_PRECISION",
                2
            ),

            2
        ),

    "quantity_precision":

        positive_int(

            getattr(
                settings,
                "QUANTITY_PRECISION",
                4
            ),

            4
        ),

    # =================================================
    # LOT SIZE / NOTIONAL GUARDS
    # =================================================
    #
    # Binance rejects orders where qty < LOT_SIZE minimum or where
    # qty * price < MIN_NOTIONAL. These defaults are conservative
    # estimates for testnet/mainnet spot -- the real minimums vary
    # by symbol (BTCUSDT: 0.00001 BTC, ETHUSDT: 0.0001 ETH, both
    # with $10 notional minimum on mainnet). With $10 of capital
    # and RISK=0.25%, the risk amount per trade is $0.025 -- far
    # below any symbol's notional minimum. The RiskAgent checks
    # these before placing a real order so the failure is logged as
    # INVALID_POSITION_SIZE rather than a Binance API error.
    #
    # Set in .env:
    #   MIN_ORDER_QUANTITY=0.00001   # absolute quantity floor
    #   MIN_ORDER_NOTIONAL=1.0       # quantity * entry_price floor

    "min_order_quantity":

        positive_float(

            getattr(
                settings,
                "MIN_ORDER_QUANTITY",
                0.00001
            ),

            0.00001
        ),

    "min_order_notional":

        positive_float(

            getattr(
                settings,
                "MIN_ORDER_NOTIONAL",
                0.0
            ),

            0.0
        )
}
