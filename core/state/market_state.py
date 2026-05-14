# -*- coding: utf-8 -*-

from datetime import datetime


class MarketState:

    def __init__(self):

        # =================================================
        # MARKET DATA
        # =================================================

        self.candles = {}

        self.total_messages = 0

        self.last_kline_at = None

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
                self.active_symbols
        }


market_state = MarketState()