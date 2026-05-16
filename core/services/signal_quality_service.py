# -*- coding: utf-8 -*-

from datetime import datetime

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

from core.utils.console_logger import (
    log
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

        valid, reason = self._validate_trend(
            payload
        )

        if not valid:
            return valid, reason

        valid, reason = self._validate_atr(
            payload
        )

        if not valid:
            return valid, reason

        valid, reason = self._validate_confidence(
            payload
        )

        if not valid:
            return valid, reason

        valid, reason = self._validate_cooldown(
            payload
        )

        if not valid:
            return valid, reason

        valid, reason = self._validate_max_positions(
            payload
        )

        if not valid:
            return valid, reason

        valid, reason = self._validate_drawdown(
            payload
        )

        if not valid:
            return valid, reason

        return True, "VALID"

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

            return True, "DISABLED"

        prices = self.trend_service.get_prices(
            user_id=payload.user_id,
            symbol=payload.symbol
        )

        slow_period = self.config[
            "ema_slow_period"
        ]

        # =====================================================
        # NOT ENOUGH DATA
        # =====================================================

        if len(prices) < slow_period:

            return True, "WARMUP"

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

        trend_strength = (
            (
                ema_fast - ema_slow
            ) / ema_slow
        ) * 100
        
        
        # =====================================================
        # SOFT FILTER
        # =====================================================

        if trend_diff < -0.50:

            return (
                False,
                "BEARISH_TREND"
            )

        return True, "OK"

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

            return True, "DISABLED"

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

        # =====================================================
        # ATR NOT READY
        # =====================================================

        if atr_percent is None:

            log(
                "ATR",
                (
                    f"{payload.symbol} "
                    f"ATR_NOT_READY"
                ),
                "WARNING"
            )

            return (
                False,
                "ATR_NOT_READY"
            )

        min_atr = self.config[
            "min_atr_percent"
        ]

        # =====================================================
        # TELEMETRY
        # =====================================================

        log(
            "ATR",
            (
                f"{payload.symbol} "
                f"atr={round(atr_percent, 4)}% "
                f"min={min_atr}%"
            ),
            "INFO"
        )

        # =====================================================
        # LOW VOLATILITY
        # =====================================================

        if atr_percent < min_atr:

            log(
                "ATR",
                (
                    f"BLOCKED "
                    f"{payload.symbol} "
                    f"LOW_VOLATILITY "
                    f"atr={round(atr_percent, 4)}%"
                ),
                "WARNING"
            )

            return (
                False,
                "LOW_VOLATILITY"
            )

        # =====================================================
        # APPROVED
        # =====================================================

        log(
            "ATR",
            (
                f"APPROVED "
                f"{payload.symbol} "
                f"atr={round(atr_percent, 4)}%"
            ),
            "SUCCESS"
        )

        return True, "OK"

    # =====================================================
    # CONFIDENCE
    # =====================================================

    def _validate_confidence(
        self,
        payload
    ):

        threshold = self.config[
            "confidence_threshold"
        ]

        confidence = getattr(
            payload,
            "signal_strength",
            0.0
        )

        if confidence < threshold:

            return (
                False,
                f"LOW_CONFIDENCE_{confidence}"
            )

        return True, "OK"

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

            return True, "DISABLED"

        key = (
            payload.user_id,
            payload.symbol
        )

        now = datetime.utcnow()

        last_trade = self.cooldowns.get(
            key
        )

        if last_trade:

            seconds = (
                now - last_trade
            ).total_seconds()

            if seconds < self.config[
                "cooldown_seconds"
            ]:

                return (
                    False,
                    "COOLDOWN_ACTIVE"
                )

        return True, "OK"

    # =====================================================
    # MAX POSITIONS
    # =====================================================

    def _validate_max_positions(
        self,
        payload
    ):

        open_positions = (
            self.trades.get_open_trades(
                user_id=payload.user_id
            )
        )

        if len(open_positions) >= self.config[
            "max_open_positions"
        ]:

            return (
                False,
                "MAX_OPEN_POSITIONS"
            )

        return True, "OK"

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

            return True, "DISABLED"

        snapshot = (
            self.portfolio.get_latest_snapshot(
                user_id=payload.user_id
            )
        )

        if not snapshot:
            return True, "NO_SNAPSHOT"

        if snapshot.drawdown >= self.config[
            "daily_drawdown_limit"
        ]:

            return (
                False,
                "DAILY_DRAWDOWN_LIMIT"
            )

        return True, "OK"


signal_quality_service = (
    SignalQualityService()
)