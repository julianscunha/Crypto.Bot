# -*- coding: utf-8 -*-

from datetime import (
    datetime
)

from collections import (
    defaultdict
)


class MarketState:

    def __init__(self):

        self.reset()

    # =====================================================
    # FROM PERSISTED STATE (CROSS-PROCESS)
    # =====================================================
    #
    # Reconstructs a MarketState instance from a dict shaped like
    # RuntimeStateRepository.get()'s return value, so the API
    # process can reuse snapshot()'s existing uptime/ratio
    # calculations instead of duplicating that logic. Used when the
    # API needs to report telemetry that was actually written by
    # the Runner process (a separate OS process -- see
    # data/storage/repositories/runtime_state_repository.py for why
    # this indirection exists at all).

    @classmethod
    def from_persisted(
        cls,
        data: dict
    ):

        instance = cls()

        instance.started_at = (
            data.get("started_at")
            or instance.started_at
        )

        instance.websocket_connected = bool(
            data.get(
                "websocket_connected",
                False
            )
        )

        instance.total_market_messages = int(
            data.get(
                "total_market_messages",
                0
            )
        )

        instance.last_market_message_at = (
            data.get(
                "last_market_message_at"
            )
        )

        instance.active_symbols = set(
            data.get(
                "active_symbols",
                []
            )
            or []
        )

        instance.total_analysis_requests = int(
            data.get(
                "total_analysis_requests",
                0
            )
        )

        instance.total_generated_signals = int(
            data.get(
                "total_generated_signals",
                0
            )
        )

        instance.total_approved_signals = int(
            data.get(
                "total_approved_signals",
                0
            )
        )

        instance.total_rejected_signals = int(
            data.get(
                "total_rejected_signals",
                0
            )
        )

        instance.total_executed_orders = int(
            data.get(
                "total_executed_orders",
                0
            )
        )

        instance.total_closed_positions = int(
            data.get(
                "total_closed_positions",
                0
            )
        )

        instance.blocked_signal_reasons = defaultdict(
            int,
            data.get(
                "blocked_signal_reasons",
                {}
            )
            or {}
        )

        instance.execution_reasons = defaultdict(
            int,
            data.get(
                "execution_reasons",
                {}
            )
            or {}
        )

        return instance

    # =====================================================
    # RESET
    # =====================================================

    def reset(
        self
    ):

        # =================================================
        # SESSION
        # =================================================

        self.started_at = (
            datetime.utcnow()
        )

        # =================================================
        # CONNECTION
        # =================================================

        self.websocket_connected = (
            False
        )

        # =================================================
        # MARKET INGESTION
        # =================================================

        self.total_market_messages = 0

        self.last_market_message_at = (
            None
        )

        self.active_symbols = (
            set()
        )

        # =================================================
        # ANALYSIS PIPELINE
        # =================================================

        self.total_analysis_requests = 0

        self.total_generated_signals = 0

        self.total_approved_signals = 0

        self.total_rejected_signals = 0

        # =================================================
        # EXECUTION PIPELINE
        # =================================================

        self.total_executed_orders = 0

        self.total_closed_positions = 0

        # =================================================
        # TELEMETRY
        # =================================================

        self.blocked_signal_reasons = (
            defaultdict(int)
        )

        self.execution_reasons = (
            defaultdict(int)
        )

    # =====================================================
    # CONNECTION
    # =====================================================

    def set_websocket_connected(
        self,
        connected: bool
    ):

        self.websocket_connected = (
            bool(connected)
        )

    # =====================================================
    # MARKET INGESTION
    # =====================================================

    def register_market_message(
        self,
        symbol: str
    ):

        self.total_market_messages += 1

        self.last_market_message_at = (
            datetime.utcnow()
        )

        if symbol:

            self.active_symbols.add(
                symbol
            )

    # =====================================================
    # KLINE (alias used by ingestion clients)
    # =====================================================

    def register_kline(
        self,
        symbol: str
    ):

        self.register_market_message(
            symbol
        )

    # =====================================================
    # ANALYSIS
    # =====================================================

    def register_analysis_request(
        self
    ):

        self.total_analysis_requests += 1

    # =====================================================
    # SIGNAL GENERATED
    # =====================================================

    def register_generated_signal(
        self
    ):

        self.total_generated_signals += 1

    # =====================================================
    # SIGNAL APPROVED
    # =====================================================

    def register_approved_signal(
        self
    ):

        self.total_approved_signals += 1

    # =====================================================
    # SIGNAL REJECTED
    # =====================================================

    def register_rejected_signal(
        self,
        reason: str
    ):

        self.total_rejected_signals += 1

        self.blocked_signal_reasons[
            reason
        ] += 1

    # =====================================================
    # ORDER EXECUTED
    # =====================================================

    def register_order_execution(
        self,
        reason: str = "EXECUTED"
    ):

        self.total_executed_orders += 1

        self.execution_reasons[
            reason
        ] += 1

    # =====================================================
    # POSITION CLOSED
    # =====================================================

    def register_closed_position(
        self
    ):

        self.total_closed_positions += 1

    # =====================================================
    # TELEMETRY
    # =====================================================

    def get_blocked_signal_reasons(
        self
    ):

        return dict(
            self.blocked_signal_reasons
        )

    def get_execution_reasons(
        self
    ):

        return dict(
            self.execution_reasons
        )

    # =====================================================
    # METRICS
    # =====================================================

    def get_signal_generation_ratio(
        self
    ):

        if self.total_analysis_requests <= 0:

            return 0.0

        return round(

            (
                self.total_generated_signals
                /
                self.total_analysis_requests
            ) * 100,

            2
        )

    def get_signal_approval_ratio(
        self
    ):

        if self.total_generated_signals <= 0:

            return 0.0

        return round(

            (
                self.total_approved_signals
                /
                self.total_generated_signals
            ) * 100,

            2
        )

    def get_execution_ratio(
        self
    ):

        if self.total_approved_signals <= 0:

            return 0.0

        return round(

            (
                self.total_executed_orders
                /
                self.total_approved_signals
            ) * 100,

            2
        )

    # =====================================================
    # SNAPSHOT
    # =====================================================

    def snapshot(
        self
    ):

        uptime_seconds = int(

            (
                datetime.utcnow()
                -
                self.started_at
            ).total_seconds()
        )

        return {

            # =============================================
            # SESSION
            # =============================================

            "started_at":
                self.started_at,

            "uptime_seconds":
                uptime_seconds,

            # =============================================
            # CONNECTION
            # =============================================

            "websocket_connected":
                self.websocket_connected,

            # =============================================
            # MARKET
            # =============================================

            "total_market_messages":
                self.total_market_messages,

            "last_market_message_at":
                self.last_market_message_at,

            "active_symbols":
                sorted(
                    list(self.active_symbols)
                ),

            # =============================================
            # ANALYSIS PIPELINE
            # =============================================

            "total_analysis_requests":
                self.total_analysis_requests,

            "total_generated_signals":
                self.total_generated_signals,

            "total_approved_signals":
                self.total_approved_signals,

            "total_rejected_signals":
                self.total_rejected_signals,

            # =============================================
            # EXECUTION PIPELINE
            # =============================================

            "total_executed_orders":
                self.total_executed_orders,

            "total_closed_positions":
                self.total_closed_positions,

            # =============================================
            # TELEMETRY
            # =============================================

            "blocked_signal_reasons":
                self.get_blocked_signal_reasons(),

            "execution_reasons":
                self.get_execution_reasons(),

            # =============================================
            # METRICS
            # =============================================

            "signal_generation_ratio":
                self.get_signal_generation_ratio(),

            "signal_approval_ratio":
                self.get_signal_approval_ratio(),

            "execution_ratio":
                self.get_execution_ratio()
        }


market_state = (
    MarketState()
)
