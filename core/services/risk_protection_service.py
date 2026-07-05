# -*- coding: utf-8 -*-

"""
Daily circuit breakers: stops the bot from opening new positions once
either limit is hit for the current UTC day, resetting automatically
at the next day boundary.

Both limits (max_daily_loss_percent, max_daily_trades) already
existed in core/config/trading_config.py with sane defaults, but no
code anywhere actually read or enforced them -- they were config
"in name only". This service is what makes them real.

This is intentionally a separate service from SignalQualityService's
existing drawdown/position-limit checks: those measure state SINCE
THE CURRENT SESSION STARTED (peak equity, open position count) and
answer "is this signal safe to take right now". This service answers
a different, narrower question -- "has today specifically gone bad
enough that the bot should stop for the rest of the day" -- which
needs its own UTC-day boundary and its own reset behavior, not
something the session-scoped checks already happening were built to
express.
"""

from datetime import (
    datetime
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from data.storage.repositories.trades_repository import (
    trades_repository
)


class RiskProtectionService:

    def __init__(self):

        self.config = (
            TRADING_CONFIG
        )

        self.trades = (
            trades_repository
        )

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _safe_float(
        value,
        precision: int = 2
    ) -> float:

        return round(
            float(value or 0.0),
            precision
        )

    # =====================================================
    # DAILY REALIZED PNL
    # =====================================================

    def get_daily_realized_pnl(
        self,
        user_id: int
    ) -> float:

        trades_today = (

            self.trades
            .get_trades_closed_today(
                user_id=user_id
            )
        )

        return self._safe_float(

            sum(
                trade.realized_pnl or 0.0
                for trade in trades_today
            )
        )

    # =====================================================
    # DAILY TRADE COUNT
    # =====================================================

    def get_daily_trade_count(
        self,
        user_id: int
    ) -> int:

        return (

            self.trades
            .count_trades_opened_today(
                user_id=user_id
            )
        )

    # =====================================================
    # DAILY LOSS LIMIT
    # =====================================================

    def check_daily_loss_limit(
        self,
        user_id: int,
        account_balance: float
    ) -> tuple[bool, str]:

        """
        Returns (allowed, reason). allowed=False means today's
        realized loss has reached or exceeded max_daily_loss_percent
        of the configured account balance -- no new positions should
        open for the rest of the UTC day, regardless of how
        confident the current signal is.
        """

        if account_balance <= 0:

            return (
                True,
                "ACCOUNT_BALANCE_WARMUP"
            )

        daily_pnl = (

            self.get_daily_realized_pnl(
                user_id=user_id
            )
        )

        # only losses count toward this limit -- a profitable day
        # never trips it, by design
        if daily_pnl >= 0:

            return (
                True,
                "NO_DAILY_LOSS"
            )

        daily_loss_percent = (

            abs(daily_pnl)
            /
            account_balance
        ) * 100

        max_daily_loss_percent = (
            self.config[
                "max_daily_loss_percent"
            ]
        )

        if daily_loss_percent >= max_daily_loss_percent:

            return (
                False,
                "DAILY_LOSS_LIMIT_REACHED"
            )

        return (
            True,
            "WITHIN_DAILY_LOSS_LIMIT"
        )

    # =====================================================
    # DAILY TRADE LIMIT
    # =====================================================

    def check_daily_trade_limit(
        self,
        user_id: int
    ) -> tuple[bool, str]:

        """
        Returns (allowed, reason). allowed=False means
        max_daily_trades has already been reached for today --
        protects against overtrading even on a winning streak,
        since high trade frequency is itself a risk signal
        independent of whether trades so far were profitable.
        """

        trade_count = (

            self.get_daily_trade_count(
                user_id=user_id
            )
        )

        max_daily_trades = (
            self.config[
                "max_daily_trades"
            ]
        )

        if trade_count >= max_daily_trades:

            return (
                False,
                "DAILY_TRADE_LIMIT_REACHED"
            )

        return (
            True,
            "WITHIN_DAILY_TRADE_LIMIT"
        )

    # =====================================================
    # STATUS SNAPSHOT
    # =====================================================

    def get_status(
        self,
        user_id: int,
        account_balance: float
    ) -> dict:

        """
        Full daily risk status for display (dashboard) and for
        SignalQualityService's validators to check without
        duplicating this logic.
        """

        daily_pnl = (
            self.get_daily_realized_pnl(
                user_id=user_id
            )
        )

        trade_count = (
            self.get_daily_trade_count(
                user_id=user_id
            )
        )

        max_daily_loss_percent = (
            self.config[
                "max_daily_loss_percent"
            ]
        )

        max_daily_trades = (
            self.config[
                "max_daily_trades"
            ]
        )

        daily_loss_percent = (

            self._safe_float(

                (
                    abs(daily_pnl)
                    /
                    account_balance
                ) * 100
            )

            if (
                account_balance > 0
                and daily_pnl < 0
            )

            else 0.0
        )

        loss_allowed, loss_reason = (
            self.check_daily_loss_limit(
                user_id=user_id,
                account_balance=account_balance
            )
        )

        trade_allowed, trade_reason = (
            self.check_daily_trade_limit(
                user_id=user_id
            )
        )

        return {

            "trading_halted":
                not (loss_allowed and trade_allowed),

            "halt_reason":
                loss_reason
                if not loss_allowed
                else (
                    trade_reason
                    if not trade_allowed
                    else None
                ),

            "daily_pnl":
                daily_pnl,

            "daily_loss_percent":
                daily_loss_percent,

            "max_daily_loss_percent":
                max_daily_loss_percent,

            "daily_trade_count":
                trade_count,

            "max_daily_trades":
                max_daily_trades,

            "day_started_at": (

                datetime.utcnow()
                .replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0
                )
            )
        }


risk_protection_service = (
    RiskProtectionService()
)
