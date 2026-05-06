# -*- coding: utf-8 -*-

from core.contracts.messages import (
    MarketDataMessage,
    MarketAnalysisMessage,
    MarketAnalysisPayload
)

from core.services.signal_quality_service import (
    SignalQualityService
)


class AnalystAgent:

    def __init__(self, bus):

        self.bus = bus

        self.signal_quality = (
            SignalQualityService()
        )

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            MarketDataMessage
        ):
            return

        payload = message.payload

        # =====================================================
        # UPDATE TREND ENGINE
        # =====================================================

        self.signal_quality.update_market_data(
            payload
        )

        # =====================================================
        # SIMPLE ANALYSIS
        # =====================================================

        analysis = "BULLISH"

        confidence = 0.75

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

        await self.bus.publish(
            analysis_message
        )