# -*- coding: utf-8 -*-

from datetime import (
    datetime
)

from core.config.signal_quality_config import (
    SIGNAL_QUALITY_CONFIG
)

from core.services.ema_trend_service import (
    ema_trend_service
)

from core.services.atr_service import (
    atr_service
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from data.storage.repositories.portfolio_repository import (
    PortfolioRepository
)


class SignalQualityService:

    def __init__(self):

        self.config = (
            SIGNAL_QUALITY_CONFIG
        )

        self.trades = (
            trades_repository
        )

        self.portfolio = (
            PortfolioRepository()
        )

        self.cooldowns = {}

        self.trend_service = (
            ema_trend_service
        )

        self.atr_service = (
            atr_service
        )

    # =====================================================
    # REGISTER TRADE
    # =====================================================

    def register_trade(
        self,
        user_id: int,
        symbol: str
    ):

        key = (
            user_id,
            symbol
        )

        self.cooldowns[key] = (
            datetime.utcnow()
        )

    # =====================================================
    # MARKET UPDATE
    # =====================================================

    def update_market_data(
        self,
        payload
    ):

        self.trend_service.update_price(
            user_id=payload.user_id,
            symbol=payload.symbol,
            price=payload.close
        )

    # =====================================================
    # MAIN VALIDATION
    # =====================================================

    def validate(
        self,
        payload
    ) -> tuple[bool, str]:

        validators = [

            self._validate_trend,

            self._validate_atr,

            self._validate_confidence,

            self._validate_cooldown,

            self._validate_max_positions,

            self._validate_drawdown
        ]

        for validator in validators:

            valid, reason = (
                validator(payload)
            )

            if not valid:

                return (
                    False,
                    reason
                )

        return (
            True,
            "VALID"
        )

    # =====================================================
    # TREND
    # =====================================================

    def _validate_trend(
        self,
        payload
    ):

        if not self.config[
            "enable_trend_filter"
        ]:

            return (
                True,
                "DISABLED"
            )

        prices = (
            self.trend_service.get_prices(
                user_id=payload.user_id,
                symbol=payload.symbol
            )
        )

        slow_period = (
            self.config[
                "ema_slow_period"
            ]
        )

        # =================================================
        # WARMUP
        # =================================================

        if len(prices) < slow_period:

            return (
                True,
                "WARMUP"
            )

        ema_fast = (

            self.trend_service
            .calculate_ema(

                prices=prices,

                period=self.config[
                    "ema_fast_period"
                ]
            )
        )

        ema_slow = (

            self.trend_service
            .calculate_ema(

                prices=prices,

                period=slow_period
            )
        )

        # =================================================
        # SAFETY
        # =================================================

        if ema_fast is None:

            return (
                False,
                "EMA_FAST_INVALID"
            )

        if ema_slow is None:

            return (
                False,
                "EMA_SLOW_INVALID"
            )

        if ema_slow <= 0:

            return (
                False,
                "EMA_DIVISION_INVALID"
            )

        trend_strength = round(

            (
                (
                    ema_fast
                    -
                    ema_slow
                )

                / ema_slow
            ) * 100,

            4
        )

        bearish_threshold = (
            self.config.get(
                "bearish_threshold",
                -0.50
            )
        )

        if trend_strength < bearish_threshold:

            return (
                False,
                "BEARISH_TREND"
            )

        return (
            True,
            "OK"
        )

    # =====================================================
    # ATR
    # =====================================================

    def _validate_atr(
        self,
        payload
    ):

        if not self.config[
            "enable_volatility_filter"
        ]:

            return (
                True,
                "DISABLED"
            )

        atr_percent = (

            self.atr_service
            .calculate_atr_percent(

                user_id=payload.user_id,

                symbol=payload.symbol,

                period=self.config[
                    "atr_period"
                ]
            )
        )

        if atr_percent is None:

            return (
                False,
                "ATR_NOT_READY"
            )

        min_atr = (
            self.config[
                "min_atr_percent"
            ]
        )

        if atr_percent < min_atr:

            return (
                False,
                "LOW_VOLATILITY"
            )

        return (
            True,
            "OK"
        )

    # =====================================================
    # CONFIDENCE
    # =====================================================

    def _validate_confidence(
        self,
        payload
    ):

        threshold = (
            self.config[
                "confidence_threshold"
            ]
        )

        confidence = round(

            getattr(
                payload,
                "signal_strength",
                0.0
            ),

            2
        )

        if confidence < threshold:

            return (
                False,
                "LOW_CONFIDENCE"
            )

        return (
            True,
            "OK"
        )

    # =====================================================
    # COOLDOWN
    # =====================================================

    def _validate_cooldown(
        self,
        payload
    ):

        if not self.config[
            "enable_cooldown"
        ]:

            return (
                True,
                "DISABLED"
            )

        key = (
            payload.user_id,
            payload.symbol
        )

        last_trade = (
            self.cooldowns.get(key)
        )

        if not last_trade:

            return (
                True,
                "OK"
            )

        elapsed_seconds = (

            datetime.utcnow()
            -
            last_trade

        ).total_seconds()

        cooldown_seconds = (
            self.config[
                "cooldown_seconds"
            ]
        )

        if elapsed_seconds < cooldown_seconds:

            return (
                False,
                "COOLDOWN_ACTIVE"
            )

        return (
            True,
            "OK"
        )

    # =====================================================
    # MAX POSITIONS
    # =====================================================

    def _validate_max_positions(
        self,
        payload
    ):

        open_positions = (

            self.trades
            .get_open_trades(
                user_id=payload.user_id
            )
        )

        max_positions = (
            self.config[
                "max_open_positions"
            ]
        )

        if len(open_positions) >= max_positions:

            return (
                False,
                "MAX_OPEN_POSITIONS"
            )

        return (
            True,
            "OK"
        )

    # =====================================================
    # DRAWDOWN
    # =====================================================

    def _validate_drawdown(
        self,
        payload
    ):

        if not self.config[
            "enable_drawdown_guard"
        ]:

            return (
                True,
                "DISABLED"
            )

        snapshot = (

            self.portfolio
            .get_latest_snapshot(
                user_id=payload.user_id
            )
        )

        if not snapshot:

            return (
                True,
                "NO_SNAPSHOT"
            )

        drawdown_limit = (
            self.config[
                "daily_drawdown_limit"
            ]
        )

        if snapshot.drawdown >= drawdown_limit:

            return (
                False,
                "DAILY_DRAWDOWN_LIMIT"
            )

        return (
            True,
            "OK"
        )


signal_quality_service = (
    SignalQualityService()
)