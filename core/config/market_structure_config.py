# -*- coding: utf-8 -*-

MARKET_STRUCTURE_CONFIG = {

    # =====================================================
    # SWING DETECTION
    # =====================================================

    "swing_window": 2,

    # =====================================================
    # TREND STRUCTURE
    # =====================================================

    "require_bos_confirmation": True,

    "min_trend_strength": 1,

    # =====================================================
    # CONSOLIDATION
    # =====================================================

    "enable_consolidation_filter": True,

    "consolidation_threshold": 0.001,

    # =====================================================
    # BREAKOUT FILTER
    # =====================================================

    "enable_fake_breakout_filter": True
}