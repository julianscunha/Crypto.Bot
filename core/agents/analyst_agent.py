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

from core.services.atr_service import (
    atr_service
)

from colorama import (
    Fore,
    Style,
    init
)

from core.utils.console_logger import (
    log
)

class AnalystAgent:

    def __init__(self, bus):

        self.bus = bus

        self.signal_quality = (
            SignalQualityService()
        )

        self.market_structure = (
            market_structure_service
        )

        self.atr_service = atr_service

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
        # UPDATE MARKET STRUCTURE
        # =====================================================

        self.market_structure.update_market_data(
            user_id=payload.user_id,
            symbol=payload.symbol,
            price=payload.close
        )

        # =====================================================
        # UPDATE ATR ENGINE
        # =====================================================

        self.atr_service.update_candle(
            user_id=payload.user_id,
            symbol=payload.symbol,
            high=payload.high,
            low=payload.low,
            close=payload.close
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