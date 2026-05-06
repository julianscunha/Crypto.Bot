# -*- coding: utf-8 -*-

from datetime import datetime

from core.config.signal_quality_config import (
    SIGNAL_QUALITY_CONFIG
)

from data.storage.repositories.trades_repository import (
    TradesRepository
)

from data.storage.repositories.portfolio_repository import (
    PortfolioRepository
)


class SignalQualityService:

    def __init__(self):

        self.config = SIGNAL_QUALITY_CONFIG

        self.trades = TradesRepository()

        self.portfolio = PortfolioRepository()

        self.cooldowns = {}

    # =====================================================
    # MAIN VALIDATION
    # =====================================================

    def validate(
        self,
        payload
    ) -> tuple[bool, str]:

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

        self.cooldowns[key] = now

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

        if snapshot.drawdown <= self.config[
            "daily_drawdown_limit"
        ]:

            return (
                False,
                "DAILY_DRAWDOWN_LIMIT"
            )

        return True, "OK"
