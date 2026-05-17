# -*- coding: utf-8 -*-

from core.contracts.messages import (

    MarketDataMessage,

    MarketAnalysisMessage,

    MarketAnalysisPayload
)

from core.services.signal_quality_service import (
    SignalQualityService
)

from core.services.market_structure_service import (
    market_structure_service
)

from core.services.market_regime_service import (
    market_regime_service
)

from core.services.atr_service import (
    atr_service
)

from core.utils.console_logger import (
    log
)


class AnalystAgent:

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

        self.market_regime = (
            market_regime_service
        )

        self.atr_service = (
            atr_service
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
            MarketDataMessage
        ):

            return

        payload = (
            message.payload
        )

        # =================================================
        # UPDATE TREND ENGINE
        # =================================================

        self.signal_quality.update_market_data(
            payload
        )

        # =================================================
        # UPDATE STRUCTURE ENGINE
        # =================================================

        self.market_structure.update_market_data(

            user_id=payload.user_id,

            symbol=payload.symbol,

            price=payload.close
        )

        # =================================================
        # UPDATE ATR ENGINE
        # =================================================

        self.atr_service.update_candle(

            user_id=payload.user_id,

            symbol=payload.symbol,

            high=payload.high,

            low=payload.low,

            close=payload.close
        )

        # =================================================
        # UPDATE REGIME ENGINE
        # =================================================

        self.market_regime.update_price(

            symbol=payload.symbol,

            close=payload.close
        )

        regime = (

            self.market_regime
            .detect_regime(
                payload.symbol
            )
        )

        # =================================================
        # REGIME CHANGED
        # =================================================

        if self.market_regime.has_changed(
            payload.symbol,
            regime
        ):

            log(
                "MARKET",
                f"REGIME {regime}"
            )

        # =================================================
        # MARKET STRUCTURE
        # =================================================

        structure = (

            self.market_structure
            .analyze_structure(

                user_id=payload.user_id,

                symbol=payload.symbol
            )
        )

        # =================================================
        # ATR
        # =================================================

        atr_percent = (

            self.atr_service
            .calculate_atr_percent(

                user_id=payload.user_id,

                symbol=payload.symbol
            )
        )

        # =================================================
        # CONFIDENCE MODEL
        # =================================================

        confidence = 0.50

        # =================================================
        # STRUCTURE BONUS
        # =================================================

        if structure["valid"]:

            confidence += 0.20

        # =================================================
        # REGIME BONUS
        # =================================================

        if regime in [

            "TRENDING",

            "BULLISH"
        ]:

            confidence += 0.15

        # =================================================
        # VOLATILITY BONUS
        # =================================================

        if atr_percent is not None:

            if atr_percent >= 0.30:

                confidence += 0.10

        confidence = round(
            min(confidence, 1.0),
            2
        )

        # =================================================
        # ANALYSIS
        # =================================================

        analysis = (
            "BULLISH"
            if structure["valid"]
            else "NEUTRAL"
        )

        # =================================================
        # PAYLOAD
        # =================================================

        analysis_payload = (
            MarketAnalysisPayload(

                user_id=payload.user_id,

                symbol=payload.symbol,

                analysis=analysis,

                reference_price=payload.close,

                confidence=confidence
            )
        )

        analysis_message = (
            MarketAnalysisMessage(

                sender="AnalystAgent",

                payload=analysis_payload
            )
        )

        # =================================================
        # ANALYSIS LOG
        # =================================================

        log(
            "ANALYST",
            (
                f"{analysis} "
                f"confidence={confidence}"
            )
        )

        # =================================================
        # PUBLISH
        # =================================================

        await self.bus.publish(
            analysis_message
        )