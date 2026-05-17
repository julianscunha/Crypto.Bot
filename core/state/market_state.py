# -*- coding: utf-8 -*-

from datetime import datetime

from collections import defaultdict


class MarketState:

    def __init__(self):

        # =================================================
        # MARKET DATA
        # =================================================

        self.candles = {}

        self.total_messages = 0

        self.last_kline_at = None

        # =================================================
        # TELEMETRY
        # =================================================

        self.blocked_signals = (
            defaultdict(int)
        )

        self.generated_signals = 0

        # =================================================
        # RUNTIME
        # =================================================

        self.started_at = datetime.utcnow()

        self.websocket_connected = False

        self.active_symbols = []

    # =====================================================
    # WEBSOCKET
    # =====================================================

    def set_websocket_connected(
        self,
        connected: bool
    ):

        self.websocket_connected = connected

    # =====================================================
    # MARKET DATA
    # =====================================================

    def register_kline(
        self,
        symbol: str
    ):

        self.total_messages += 1

        self.last_kline_at = (
            datetime.utcnow()
        )

        if symbol not in self.active_symbols:

            self.active_symbols.append(
                symbol
            )

    # =====================================================
    # SIGNAL TELEMETRY
    # =====================================================

    def increment_block_reason(
        self,
        reason: str
    ):

        self.blocked_signals[
            reason
        ] += 1

    def increment_accepted_signal(
        self
    ):

        self.generated_signals += 1

    # =====================================================
    # TELEMETRY SNAPSHOT
    # =====================================================

    def get_blocked_signals(self):

        return dict(
            self.blocked_signals
        )

    def get_total_blocked_signals(
        self
    ):

        return sum(
            self.blocked_signals.values()
        )

    def get_acceptance_ratio(
        self
    ):

        total = (
            self.generated_signals
            +
            self.get_total_blocked_signals()
        )

        if total == 0:
            return 0.0

        return round(
            (
                self.generated_signals
                / total
            ) * 100,
            2
        )

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(self):

        uptime = (
            datetime.utcnow()
            - self.started_at
        ).total_seconds()

        return {

            "started_at":
                self.started_at,

            "uptime_seconds":
                int(uptime),

            "websocket_connected":
                self.websocket_connected,

            "total_messages":
                self.total_messages,

            "last_kline_at":
                self.last_kline_at,

            "active_symbols":
                self.active_symbols,

            "blocked_signals":
                self.get_blocked_signals(),

            "generated_signals":
                self.generated_signals,

            "acceptance_ratio":
                self.get_acceptance_ratio()
        }


market_state = MarketState()