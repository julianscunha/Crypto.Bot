# -*- coding: utf-8 -*-

from core.config.settings import settings


TRADING_CONFIG = {

    # =====================================================
    # POSITION
    # =====================================================

    "risk_per_trade_percent": (
        settings.RISK_PER_TRADE_PERCENT
    ),

    "account_balance": (
        settings.ACCOUNT_BALANCE
    ),

    "max_open_positions": (
        settings.MAX_OPEN_POSITIONS
    ),

    "max_position_exposure_percent": (
        settings.MAX_POSITION_EXPOSURE_PERCENT
    ),

    "max_daily_loss_percent": (
        settings.MAX_DAILY_LOSS_PERCENT
    ),

    "max_daily_trades": (
        settings.MAX_DAILY_TRADES
    ),

    # =====================================================
    # ATR RISK
    # =====================================================

    "atr_stop_multiplier":
        settings.ATR_STOP_MULTIPLIER,
    
    "atr_take_profit_multiplier":
        settings.ATR_TAKE_PROFIT_MULTIPLIER,
    
    "atr_trailing_multiplier":
        settings.ATR_TRAILING_MULTIPLIER,

    # =====================================================
    # STRUCTURE
    # =====================================================

    "min_structure_candles":
    settings.MIN_STRUCTURE_CANDLES,

    # =====================================================
    # MARKET
    # =====================================================

    "symbols": (
        settings.SYMBOLS
    ),

    "kline_interval": (
        settings.KLINE_INTERVAL
    ),

    # =====================================================
    # EXECUTION
    # =====================================================

    "mode": (
        settings.MODE
    ),

    "paper_execution": (
        settings.ENABLE_PAPER_EXECUTION
    ),

    "enable_optimizer": (
        settings.ENABLE_OPTIMIZER
    ),

    "enable_market_regime": (
        settings.ENABLE_MARKET_REGIME
    ),

    "enable_replay": (
        settings.ENABLE_REPLAY
    ),

    # =====================================================
    # BINANCE
    # =====================================================

    "binance_testnet": (
        settings.BINANCE_TESTNET
    )
}