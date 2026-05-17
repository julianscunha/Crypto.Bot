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

from core.utils.console_logger import (
    log
)

from data.features.indicators import (
    atr
)


class StrategyAgent:

    def __init__(
        self,
        bus
    ):

        self.bus = bus

        self.signal_quality = (
            SignalQualityService()
        )

        self.market_structure = (
            market_structure_service
        )

        self.bus.subscribe(
            self
        )

    # =====================================================
    # MESSAGE
    # =====================================================

    async def on_message(
        self,
        message
    ):

        if not isinstance(
            message,
            MarketAnalysisMessage
        ):

            return

        payload = (
            message.payload
        )

        # =================================================
        # MARKET DATA
        # =================================================

        prices = (

            self.market_structure
            .get_prices(

                payload.user_id,

                payload.symbol
            )
        )

        if not prices:

            market_state.increment_block_reason(
                "NO_MARKET_DATA"
            )

            return

        # =================================================
        # ATR
        # =================================================

        atr_value = atr(
            prices
        )

        if atr_value is None:

            market_state.increment_block_reason(
                "ATR_NOT_READY"
            )

            return

        if atr_value <= 0:

            market_state.increment_block_reason(
                "INVALID_ATR"
            )

            return

        # =================================================
        # STRUCTURE
        # =================================================

        structure = (

            self.market_structure
            .analyze_structure(

                user_id=payload.user_id,

                symbol=payload.symbol
            )
        )

        # =================================================
        # STRUCTURE FILTER
        # =================================================

        if not structure["valid"]:

            market_state.increment_block_reason(
                structure["reason"]
            )

            return

        # =================================================
        # SIGNAL
        # =================================================

        signal_payload = (
            StrategySignalPayload(

                user_id=payload.user_id,

                symbol=payload.symbol,

                signal="BUY",

                entry_price=payload.reference_price,

                signal_strength=round(

                    getattr(
                        payload,
                        "confidence",
                        0.50
                    ),

                    2
                ),

                atr=atr_value
            )
        )

        # =================================================
        # SIGNAL QUALITY
        # =================================================

        valid, reason = (

            self.signal_quality
            .validate(
                signal_payload
            )
        )

        if not valid:

            market_state.increment_block_reason(
                reason
            )

            return

        # =================================================
        # GENERATED SIGNAL
        # =================================================

        market_state.increment_generated_signal()

        log(
            "STRATEGY",
            (
                f"SIGNAL BUY "
                f"strength={signal_payload.signal_strength}"
            ),
            "SUCCESS"
        )

        # =================================================
        # PUBLISH
        # =================================================

        signal_message = (
            StrategySignalMessage(

                sender="StrategyAgent",

                payload=signal_payload
            )
        )

        await self.bus.publish(
            signal_message
        )