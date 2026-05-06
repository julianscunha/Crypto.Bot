# -*- coding: utf-8 -*-

# =========================================================
# TREND FILTER REAL
# =========================================================
#
# Objetivo:
# - Implementar EMA Trend Engine
# - Adicionar direção real de mercado
# - Reduzir BUY contra tendência
# - Integrar no SignalQualityService
#
# Execução:
# python .\scripts\trend_filter_real.py
#
# =========================================================

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


# =========================================================
# HELPERS
# =========================================================

def write_file(path: Path, content: str):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        content.strip() + "\n",
        encoding="utf-8"
    )

    print(f"[OK] {path}")


# =========================================================
# EMA SERVICE
# =========================================================

EMA_TREND_SERVICE = r'''
# -*- coding: utf-8 -*-

from collections import defaultdict


class EmaTrendService:

    def __init__(self):

        self.market_history = defaultdict(list)

    # =====================================================
    # UPDATE PRICE
    # =====================================================

    def update_price(
        self,
        user_id: int,
        symbol: str,
        price: float
    ):

        key = (
            user_id,
            symbol
        )

        history = self.market_history[key]

        history.append(price)

        if len(history) > 200:

            history.pop(0)

    # =====================================================
    # EMA
    # =====================================================

    def calculate_ema(
        self,
        prices: list,
        period: int
    ):

        if len(prices) < period:
            return None

        multiplier = (
            2 / (period + 1)
        )

        ema = (
            sum(prices[:period]) / period
        )

        for price in prices[period:]:

            ema = (
                (price - ema)
                * multiplier
            ) + ema

        return ema

    # =====================================================
    # TREND VALIDATION
    # =====================================================

    def is_bullish(
        self,
        user_id: int,
        symbol: str,
        fast_period: int,
        slow_period: int
    ):

        key = (
            user_id,
            symbol
        )

        prices = self.market_history[key]

        ema_fast = self.calculate_ema(
            prices,
            fast_period
        )

        ema_slow = self.calculate_ema(
            prices,
            slow_period
        )

        if ema_fast is None:
            return False

        if ema_slow is None:
            return False

        return ema_fast > ema_slow
'''


# =========================================================
# SIGNAL QUALITY SERVICE
# =========================================================

SIGNAL_QUALITY_SERVICE = r'''
# -*- coding: utf-8 -*-

from datetime import datetime

from core.config.signal_quality_config import (
    SIGNAL_QUALITY_CONFIG
)

from core.services.ema_trend_service import (
    EmaTrendService
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

        self.trend_service = (
            EmaTrendService()
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

        bullish = (
            self.trend_service.is_bullish(
                user_id=payload.user_id,
                symbol=payload.symbol,
                fast_period=self.config[
                    "ema_fast_period"
                ],
                slow_period=self.config[
                    "ema_slow_period"
                ]
            )
        )

        if not bullish:

            return (
                False,
                "BEARISH_TREND"
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
'''


# =========================================================
# ANALYST AGENT
# =========================================================

ANALYST_AGENT_APPEND = r'''

# =====================================================
# TREND UPDATE
# =====================================================

self.signal_quality.update_market_data(
    payload
)
'''


# =========================================================
# README
# =========================================================

README_APPEND = r'''

# =========================================================
# EMA TREND ENGINE
# =========================================================

## COMPONENTS

- EmaTrendService
- EMA Fast
- EMA Slow
- Bullish Trend Validation

## FLOW

MarketData
    -> update_price()
    -> EMA Calculation
    -> Trend Validation
    -> SignalQualityService

## VALIDATION

BUY permitido apenas quando:

EMA_FAST > EMA_SLOW

## CONFIG

Arquivo:
core/config/signal_quality_config.py

Variáveis:
- ema_fast_period
- ema_slow_period
- enable_trend_filter
'''


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("========================================")
    print("TREND FILTER REAL")
    print("========================================")
    print()

    write_file(
        ROOT / "core/services/ema_trend_service.py",
        EMA_TREND_SERVICE
    )

    write_file(
        ROOT / "core/services/signal_quality_service.py",
        SIGNAL_QUALITY_SERVICE
    )

    readme_path = ROOT / "README_FULL.md"

    if readme_path.exists():

        content = readme_path.read_text(
            encoding="utf-8"
        )

        if "EMA TREND ENGINE" not in content:

            content += README_APPEND

            readme_path.write_text(
                content,
                encoding="utf-8"
            )

            print("[OK] README_FULL.md updated")

    print()
    print("[DONE] Trend Filter REAL generated")
    print()
    print("NEXT:")
    print("1. integrar update_market_data()")
    print("2. reduzir cooldown")
    print("3. validar EMA crossover")
    print()


if __name__ == "__main__":

    main()