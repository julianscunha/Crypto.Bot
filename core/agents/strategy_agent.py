# -*- coding: utf-8 -*-

from core.contracts.messages import (

    MarketAnalysisMessage,

    StrategySignalMessage,

    StrategySignalPayload
)

from core.services.signal_quality_service import (
    signal_quality_service
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

from core.config.strategy_config import (
    STRATEGY_CONFIG
)


class StrategyAgent:

    def __init__(
        self,
        bus
    ):

        self.bus = bus

        self.signal_quality = (
            signal_quality_service
        )

        self.market_structure = (
            market_structure_service
        )

        self.strategy_config = (
            STRATEGY_CONFIG
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
        # ANALYSIS TELEMETRY
        # =================================================

        market_state.register_analysis_request()

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

            market_state.register_rejected_signal(
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

            market_state.register_rejected_signal(
                "ATR_NOT_READY"
            )

            return

        if atr_value <= 0:

            market_state.register_rejected_signal(
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

            market_state.register_rejected_signal(
                structure["reason"]
            )

            return

        # =================================================
        # CONFIDENCE
        # =================================================

        confidence = round(

            float(

                getattr(
                    payload,
                    "confidence",
                    0.50
                )
            ),

            2
        )

        minimum_signal_strength = (

            self.strategy_config[
                "minimum_signal_strength"
            ]
        )

        if confidence < minimum_signal_strength:

            market_state.register_rejected_signal(
                "LOW_SIGNAL_STRENGTH"
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

                signal_strength=confidence,

                # rounding to 2 decimals here used to truncate the raw
                # ATR to 0.00 for low-priced symbols (e.g. DOGEUSDT,
                # where a real ATR of a few thousandths of a dollar is
                # smaller than one cent) -- RiskAgent then rejected
                # every single signal as INVALID_ATR (payload.atr <= 0),
                # even though the underlying ATR was perfectly valid.
                # Final order prices are still rounded to the exchange's
                # configured price_precision downstream in RiskAgent, so
                # this doesn't affect what actually gets sent to Binance.
                atr=round(
                    atr_value,
                    8
                )
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

            market_state.register_rejected_signal(
                reason
            )

            return

        # =================================================
        # GENERATED SIGNAL
        # =================================================

        market_state.register_generated_signal()

        # =================================================
        # TELEMETRY
        # =================================================

        log(
            "STRATEGY",
            (
                f"SIGNAL BUY "
                f"strength={signal_payload.signal_strength} "
                f"atr={signal_payload.atr}"
            ),
            "SUCCESS"
        )

        # =================================================
        # MESSAGE
        # =================================================

        signal_message = (
            StrategySignalMessage(

                sender="StrategyAgent",

                payload=signal_payload
            )
        )

        # =================================================
        # PUBLISH
        # =================================================

        await self.bus.publish(
            signal_message
        )
