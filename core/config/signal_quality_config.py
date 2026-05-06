# -*- coding: utf-8 -*-

SIGNAL_QUALITY_CONFIG = {

    # =====================================================
    # CONFIDENCE
    # =====================================================

    "confidence_threshold": 0.70,

    # =====================================================
    # COOLDOWN
    # =====================================================

    "enable_cooldown": True,

    "cooldown_seconds": 15,

    # =====================================================
    # TREND FILTER
    # =====================================================

    "enable_trend_filter": True,

    "ema_fast_period": 3,

    "ema_slow_period": 7,

    # =====================================================
    # VOLATILITY FILTER
    # =====================================================

    "enable_volatility_filter": True,

    "min_atr_percent": 0.40,

    # =====================================================
    # RISK CONTROL
    # =====================================================

    "max_open_positions": 3,

    "daily_drawdown_limit": -5.0,

    "enable_drawdown_guard": True
}
