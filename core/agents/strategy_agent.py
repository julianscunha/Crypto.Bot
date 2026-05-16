# -*- coding: utf-8 -*-

from core.contracts.messages import (
    MarketAnalysisMessage,
    StrategySignalMessage,
    StrategySignalPayload
)

from core.services.signal_quality_service import (
    SignalQualityService
)

from core.services.market_structure_service import (
    market_structure_service
)

from core.state.market_state import (
    market_state
)

from colorama import (
    Fore,
    Style,
    init
)

from core.utils.console_logger import (
    log
)

from data.features.indicators import atr


class StrategyAgent:

    def __init__(self, bus):

        self.bus = bus

        self.signal_quality = (
            SignalQualityService()
        )

        self.market_structure = (
            market_structure_service
        )

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            MarketAnalysisMessage
        ):
            return

        payload = message.payload

        log(
            "STRATEGY",
            f"ANALYZING {payload.symbol}"
        )

        candles_count = len(
            self.market_structure.get_prices(
                payload.user_id,
                payload.symbol
            )
        )

        log(
            "STRATEGY",
            f"STRUCTURE {payload.symbol} candles={candles_count}"
        )

        # =====================================================
        # SIMPLE STRATEGY
        # =====================================================

        signal = "BUY"

        signal_strength = getattr(
            payload,
            "confidence",
            0.50
        )

        prices = (
            self.market_structure.get_prices(
                payload.user_id,
                payload.symbol
            )
        )

        atr_value = atr(prices)

        # =====================================================
        # ATR VALIDATION
        # =====================================================

        if atr_value is None:

            log(
                "STRATEGY",
                (
                    f"SIGNAL BLOCKED "
                    f"{payload.symbol} "
                    f"| ATR_NOT_READY"
                ),
                "ERROR"
            )

            market_state.increment_block_reason(
                "ATR_NOT_READY"
            )

            return

        signal_payload = (
            StrategySignalPayload(
                user_id=payload.user_id,
                symbol=payload.symbol,
                signal=signal,
                entry_price=payload.reference_price,
                signal_strength=signal_strength,
                atr=atr_value
            )
        )

        # =====================================================
        # MARKET STRUCTURE VALIDATION
        # =====================================================

        structure = (
            self.market_structure
            .analyze_structure(
                user_id=payload.user_id,
                symbol=payload.symbol
            )
        )

        structure_valid = (
            structure["valid"]
        )

        # =====================================================
        # SIGNAL QUALITY VALIDATION
        # =====================================================

        valid, reason = (
            self.signal_quality.validate(
                signal_payload
            )
        )

        if not valid:

            log(
                "STRATEGY",
                (
                    f"SIGNAL BLOCKED "
                    f"{payload.symbol} "
                    f"| {reason}"
                ),
                "ERROR"
            )

            market_state.increment_block_reason(
                reason
            )

            return

        # =====================================================
        # FINAL STRUCTURE BLOCK
        # =====================================================

        # TODO:
        # Reativar market structure validation
        # após dataset real e tuning estrutural

        # if not structure_valid:
        #
        #     log(
        #         "STRATEGY",
        #         (
        #             f"STRUCTURE BLOCKED "
        #             f"{payload.symbol} "
        #             f"| {structure['reason']}"
        #         ),
        #         "WARNING"
        #     )
        #
        #     market_state.increment_block_reason(
        #         structure["reason"]
        #     )
        #
        #     return

        log(
            "STRATEGY",
            (
                f"SIGNAL BUY "
                f"{payload.symbol} "
                f"strength={signal_strength}"
            ),
            "SUCCESS"
        )
        
        market_state.increment_accepted_signal()

        # =====================================================
        # PUBLISH
        # =====================================================

        signal_message = (
            StrategySignalMessage(
                sender="StrategyAgent",
                payload=signal_payload
            )
        )

        await self.bus.publish(
            signal_message
        )