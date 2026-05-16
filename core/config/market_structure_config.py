# -*- coding: utf-8 -*-

MARKET_STRUCTURE_CONFIG = {

    # =====================================================
    # SWING DETECTION
    # =====================================================

    "swing_window": 2,#3

    # =====================================================
    # TREND STRUCTURE
    # =====================================================

    "require_bos_confirmation": False,

    "min_trend_strength": 2,

    # =====================================================
    # CONSOLIDATION
    # =====================================================

    "enable_consolidation_filter": True,

    "consolidation_threshold": 0.003,

    # =====================================================
    # BREAKOUT FILTER
    # =====================================================

    "enable_fake_breakout_filter": True
}