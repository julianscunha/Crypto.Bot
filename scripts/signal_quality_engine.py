# -*- coding: utf-8 -*-

# =========================================================
# SIGNAL QUALITY ENGINE
# =========================================================
#
# Objetivo:
# - Criar SignalQualityService
# - Criar SignalQualityConfig
# - Integrar filtros quantitativos
# - Atualizar README_FULL.md
#
# Execução:
# python .\scripts\signal_quality_engine.py
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
# CONFIG
# =========================================================

SIGNAL_QUALITY_CONFIG = r'''
# -*- coding: utf-8 -*-

SIGNAL_QUALITY_CONFIG = {

    # =====================================================
    # CONFIDENCE
    # =====================================================

    "confidence_threshold": 0.70,

    # =====================================================
    # COOLDOWN
    # =====================================================

    "enable_cooldown": True,

    "cooldown_seconds": 120,

    # =====================================================
    # TREND FILTER
    # =====================================================

    "enable_trend_filter": True,

    "ema_fast_period": 9,

    "ema_slow_period": 21,

    # =====================================================
    # VOLATILITY FILTER
    # =====================================================

    "enable_volatility_filter": True,

    "min_atr_percent": 0.40,

    # =====================================================
    # RISK CONTROL
    # =====================================================

    "max_open_positions": 3,

    "daily_drawdown_limit": -5.0,

    "enable_drawdown_guard": True
}
'''


# =========================================================
# SERVICE
# =========================================================

SIGNAL_QUALITY_SERVICE = r'''
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
'''


# =========================================================
# README
# =========================================================

README_APPEND = r'''

# =========================================================
# SIGNAL QUALITY ENGINE
# =========================================================

## COMPONENTS

- SignalQualityService
- Confidence Threshold
- Cooldown Engine
- Drawdown Protection
- Position Limiter
- Frontend Config Ready

## FLOW

StrategySignal
    -> SignalQualityService
    -> RiskAgent
    -> ExecutionAgent

## VALIDATIONS

- confidence threshold
- cooldown validation
- max open positions
- drawdown guard

## FRONTEND READY

Arquivo:
core/config/signal_quality_config.py

Variáveis:
- confidence_threshold
- cooldown_seconds
- max_open_positions
- daily_drawdown_limit
- ema_fast_period
- ema_slow_period
- min_atr_percent

Todos os parâmetros podem ser:
- editados manualmente
- controlados pelo frontend
- ajustados por IA
- persistidos futuramente em banco
'''


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("========================================")
    print("SIGNAL QUALITY ENGINE")
    print("========================================")
    print()

    # config

    write_file(
        ROOT / "core/config/signal_quality_config.py",
        SIGNAL_QUALITY_CONFIG
    )

    # service

    write_file(
        ROOT / "core/services/signal_quality_service.py",
        SIGNAL_QUALITY_SERVICE
    )

    # readme

    readme_path = ROOT / "README_FULL.md"

    if readme_path.exists():

        content = readme_path.read_text(
            encoding="utf-8"
        )

        if "SIGNAL QUALITY ENGINE" not in content:

            content += README_APPEND

            readme_path.write_text(
                content,
                encoding="utf-8"
            )

            print("[OK] README_FULL.md updated")

    print()
    print("[DONE] Signal Quality Engine generated")
    print()

    print("NEXT:")
    print("1. integrar SignalQualityService no StrategyAgent")
    print("2. testar cooldown")
    print("3. validar drawdown protection")
    print()


if __name__ == "__main__":

    main()