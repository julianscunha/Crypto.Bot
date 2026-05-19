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
    portfolio_repository
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
            portfolio_repository
        )

        self.trend_service = (
            ema_trend_service
        )

        self.atr_service = (
            atr_service
        )

        # =================================================
        # RUNTIME STATE
        # =================================================

        self.signal_cooldowns = {}

    # =====================================================
    # INTERNAL
    # =====================================================

    @staticmethod
    def _safe_float(
        value,
        fallback=0.0
    ):

        try:

            return float(value)

        except Exception:

            return fallback

    def _build_key(
        self,
        user_id: int,
        symbol: str
    ):

        return (
            user_id,
            symbol
        )

    # =====================================================
    # REGISTER TRADE
    # =====================================================

    def register_trade(
        self,
        user_id: int,
        symbol: str
    ):

        key = self._build_key(
            user_id,
            symbol
        )

        self.signal_cooldowns[key] = (
            datetime.utcnow()
        )

    # =====================================================
    # UPDATE MARKET DATA
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

            self._validate_ema_trend,

            self._validate_market_volatility,

            self._validate_signal_confidence,

            self._validate_signal_cooldown,

            self._validate_position_limit,

            self._validate_drawdown_protection
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
    # EMA TREND FILTER
    # =====================================================

    def _validate_ema_trend(
        self,
        payload
    ):

        if not self.config[
            "enable_ema_trend_filter"
        ]:

            return (
                True,
                "FILTER_DISABLED"
            )

        prices = (

            self.trend_service
            .get_prices(

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
                "EMA_WARMUP"
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
                "EMA_REFERENCE_INVALID"
            )

        trend_strength_percent = round(

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

        minimum_trend_strength = (
            self.config[
                "minimum_trend_strength_percent"
            ]
        )

        # =================================================
        # TREND VALIDATION
        # =================================================

        if trend_strength_percent < (

            minimum_trend_strength * -1
        ):

            return (
                False,
                "BEARISH_TREND"
            )

        return (
            True,
            "TREND_VALID"
        )

    # =====================================================
    # VOLATILITY FILTER
    # =====================================================

    def _validate_market_volatility(
        self,
        payload
    ):

        if not self.config[
            "enable_volatility_filter"
        ]:

            return (
                True,
                "FILTER_DISABLED"
            )

        atr_percent = (

            self.atr_service
            .calculate_atr_percent(

                user_id=payload.user_id,

                symbol=payload.symbol,

                period=self.config[
                    "atr_validation_period"
                ]
            )
        )

        if atr_percent is None:

            return (
                True,
                "ATR_WARMUP"
            )

        minimum_atr_percent = (
            self.config[
                "minimum_atr_percent"
            ]
        )

        if atr_percent < minimum_atr_percent:

            return (
                False,
                "LOW_VOLATILITY"
            )

        return (
            True,
            "VOLATILITY_VALID"
        )

    # =====================================================
    # SIGNAL CONFIDENCE
    # =====================================================

    def _validate_signal_confidence(
        self,
        payload
    ):

        minimum_confidence = (
            self.config[
                "minimum_signal_confidence"
            ]
        )

        signal_confidence = round(

            self._safe_float(

                getattr(
                    payload,
                    "signal_strength",
                    0.0
                )
            ),

            4
        )

        if signal_confidence < minimum_confidence:

            return (
                False,
                "LOW_CONFIDENCE"
            )

        return (
            True,
            "CONFIDENCE_VALID"
        )

    # =====================================================
    # SIGNAL COOLDOWN
    # =====================================================

    def _validate_signal_cooldown(
        self,
        payload
    ):

        if not self.config[
            "enable_signal_cooldown"
        ]:

            return (
                True,
                "FILTER_DISABLED"
            )

        key = self._build_key(

            payload.user_id,

            payload.symbol
        )

        last_signal = (
            self.signal_cooldowns.get(key)
        )

        if not last_signal:

            return (
                True,
                "COOLDOWN_READY"
            )

        elapsed_seconds = (

            datetime.utcnow()
            -
            last_signal

        ).total_seconds()

        cooldown_seconds = (
            self.config[
                "signal_cooldown_seconds"
            ]
        )

        if elapsed_seconds < cooldown_seconds:

            return (
                False,
                "SIGNAL_COOLDOWN_ACTIVE"
            )

        return (
            True,
            "COOLDOWN_READY"
        )

    # =====================================================
    # POSITION LIMIT
    # =====================================================

    def _validate_position_limit(
        self,
        payload
    ):

        open_positions = (

            self.trades
            .get_open_trades(
                user_id=payload.user_id
            )
        )

        maximum_open_positions = (
            self.config[
                "maximum_open_positions"
            ]
        )

        if len(open_positions) >= maximum_open_positions:

            return (
                False,
                "MAXIMUM_OPEN_POSITIONS"
            )

        return (
            True,
            "POSITION_LIMIT_VALID"
        )

    # =====================================================
    # DRAWDOWN PROTECTION
    # =====================================================

    def _validate_drawdown_protection(
        self,
        payload
    ):

        if not self.config[
            "enable_drawdown_protection"
        ]:

            return (
                True,
                "FILTER_DISABLED"
            )

        latest_snapshot = (

            self.portfolio
            .get_latest_snapshot(
                user_id=payload.user_id
            )
        )

        if not latest_snapshot:

            return (
                True,
                "PORTFOLIO_WARMUP"
            )

        maximum_drawdown_percent = (
            self.config[
                "maximum_daily_drawdown_percent"
            ]
        )

        if (

            latest_snapshot.drawdown
            >=
            maximum_drawdown_percent
        ):

            return (
                False,
                "MAXIMUM_DRAWDOWN_EXCEEDED"
            )

        return (
            True,
            "DRAWDOWN_VALID"
        )


signal_quality_service = (
    SignalQualityService()
)