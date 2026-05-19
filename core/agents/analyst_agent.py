# -*- coding: utf-8 -*-

from core.contracts.messages import (

    MarketDataMessage,

    MarketAnalysisMessage,

    MarketAnalysisPayload
)

from core.services.signal_quality_service import (
    signal_quality_service
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

from core.config.analyst_config import (
    ANALYST_CONFIG
)

# =====================================================
# ANALYST AGENT
# =====================================================

class AnalystAgent:

    def __init__(
        self,
        bus
    ):

        self.bus = bus

        # =================================================
        # SERVICES
        # =================================================

        self.signal_quality = (
            signal_quality_service
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

        # =================================================
        # CONFIG
        # =================================================

        self.config = (
            ANALYST_CONFIG
        )

        # =================================================
        # BUS
        # =================================================

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
        # UPDATE SIGNAL QUALITY ENGINE
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
        # REGIME CHANGE
        # =================================================

        if self.market_regime.has_changed(

            payload.symbol,

            regime
        ):

            log(
                "MARKET",
                (
                    f"REGIME_CHANGED "
                    f"symbol={payload.symbol} "
                    f"regime={regime}"
                )
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
        # VOLATILITY
        # =================================================

        atr_percent = (

            self.atr_service
            .calculate_atr_percent(

                user_id=payload.user_id,

                symbol=payload.symbol
            )
        )

        volatility_regime = (

            self.atr_service
            .get_volatility_regime(

                user_id=payload.user_id,

                symbol=payload.symbol
            )
        )

        # =================================================
        # TREND STRENGTH
        # =================================================

        trend_strength = (
            structure.get(
                "score",
                0.0
            )
        )

        # =================================================
        # CONFIDENCE MODEL
        # =================================================

        confidence = (
            self._calculate_confidence(

                structure=structure,

                regime=regime,

                atr_percent=atr_percent
            )
        )

        # =================================================
        # ANALYSIS
        # =================================================

        analysis = (
            self._determine_analysis(
                structure
            )
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

                confidence=confidence,

                market_regime=regime,

                trend_strength=trend_strength,

                volatility_regime=volatility_regime
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
                f"analysis={analysis} "
                f"confidence={confidence} "
                f"regime={regime} "
                f"volatility={volatility_regime}"
            )
        )

        # =================================================
        # PUBLISH
        # =================================================

        await self.bus.publish(
            analysis_message
        )

    # =====================================================
    # CONFIDENCE MODEL
    # =====================================================

    def _calculate_confidence(
        self,
        structure,
        regime,
        atr_percent
    ):

        confidence = (
            self.config[
                "base_confidence"
            ]
        )

        # =================================================
        # STRUCTURE BONUS
        # =================================================

        if structure.get(
            "valid",
            False
        ):

            confidence += (
                self.config[
                    "structure_bonus"
                ]
            )

        # =================================================
        # REGIME BONUS
        # =================================================

        bullish_regimes = (
            self.config[
                "bullish_regimes"
            ]
        )

        if regime in bullish_regimes:

            confidence += (
                self.config[
                    "regime_bonus"
                ]
            )

        # =================================================
        # VOLATILITY BONUS
        # =================================================

        minimum_volatility = (
            self.config[
                "minimum_volatility_percent"
            ]
        )

        if atr_percent is not None:

            if atr_percent >= minimum_volatility:

                confidence += (
                    self.config[
                        "volatility_bonus"
                    ]
                )

        # =================================================
        # NORMALIZATION
        # =================================================

        maximum_confidence = (
            self.config[
                "maximum_confidence"
            ]
        )

        return round(

            min(
                confidence,
                maximum_confidence
            ),

            2
        )

    # =====================================================
    # ANALYSIS MODEL
    # =====================================================

    @staticmethod
    def _determine_analysis(
        structure
    ):

        if structure.get(
            "valid",
            False
        ):

            return "BULLISH"

        return "NEUTRAL"