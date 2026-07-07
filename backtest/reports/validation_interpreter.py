# -*- coding: utf-8 -*-

from typing import Dict


class ValidationInterpreter:

    # =====================================================
    # PUBLIC
    # =====================================================

    def analyze(
        self,
        metrics: Dict
    ) -> Dict:

        total_trades = metrics.get(
            "total_trades",
            0
        )

        winrate = metrics.get(
            "winrate",
            0
        )

        pnl = metrics.get(
            "pnl",
            0
        )

        max_drawdown = abs(
            metrics.get(
                "max_drawdown",
                0
            )
        )

        profit_factor = metrics.get(
            "profit_factor",
            0
        )

        expectancy = metrics.get(
            "expectancy",
            0
        )

        avg_win = metrics.get(
            "avg_win",
            0
        )

        avg_loss = metrics.get(
            "avg_loss",
            0
        )

        risk_reward = metrics.get(
            "risk_reward",
            0
        )

        recovery_factor = metrics.get(
            "recovery_factor",
            0
        )

        max_win_streak = metrics.get(
            "max_win_streak",
            0
        )

        max_loss_streak = metrics.get(
            "max_loss_streak",
            0
        )

        # =================================================
        # CLASSIFICATIONS
        # =================================================

        winrate_rating = (
            self._classify_winrate(
                winrate
            )
        )

        profit_factor_rating = (
            self._classify_profit_factor(
                profit_factor
            )
        )

        drawdown_rating = (
            self._classify_drawdown(
                pnl,
                max_drawdown
            )
        )

        sample_rating = (
            self._classify_sample_size(
                total_trades
            )
        )

        rr_rating = (
            self._classify_risk_reward(
                risk_reward
            )
        )

        overfit_risk = (
            self._detect_overfit(
                winrate=winrate,
                profit_factor=profit_factor,
                pnl=pnl,
                drawdown=max_drawdown,
                trades=total_trades
            )
        )

        robustness = (
            self._calculate_robustness(
                winrate=winrate,
                profit_factor=profit_factor,
                drawdown=max_drawdown,
                trades=total_trades
            )
        )

        verdict = (
            self._generate_verdict(
                overfit_risk=overfit_risk,
                robustness=robustness,
                sample_rating=sample_rating
            )
        )

        # =================================================
        # REPORT
        # =================================================

        return {

            "performance": {

                "net_profit": pnl,
                "profit_factor": profit_factor,
                "profit_factor_rating": (
                    profit_factor_rating
                ),

                "expectancy": expectancy,

                "recovery_factor": (
                    recovery_factor
                )
            },

            "trade_quality": {

                "winrate": winrate,
                "winrate_rating": (
                    winrate_rating
                ),

                "risk_reward": risk_reward,
                "risk_reward_rating": (
                    rr_rating
                ),

                "avg_win": avg_win,
                "avg_loss": avg_loss
            },

            "risk": {

                "max_drawdown": (
                    max_drawdown
                ),

                "drawdown_rating": (
                    drawdown_rating
                ),

                "max_win_streak": (
                    max_win_streak
                ),

                "max_loss_streak": (
                    max_loss_streak
                )
            },

            "statistical_analysis": {

                "trade_sample_size": (
                    total_trades
                ),

                "sample_rating": (
                    sample_rating
                ),

                "overfit_risk": (
                    overfit_risk
                ),

                "robustness": (
                    robustness
                )
            },

            "final_verdict": verdict
        }

    # =====================================================
    # WINRATE
    # =====================================================

    def _classify_winrate(
        self,
        value: float
    ) -> str:

        if value < 0.40:
            return "LOW"

        if value < 0.60:
            return "NORMAL"

        if value < 0.75:
            return "STRONG"

        return "EXTREMELY_HIGH"

    # =====================================================
    # PROFIT FACTOR
    # =====================================================

    def _classify_profit_factor(
        self,
        value: float
    ) -> str:

        if value < 1:
            return "LOSING"

        if value < 1.5:
            return "WEAK"

        if value < 2:
            return "GOOD"

        if value < 3:
            return "EXCELLENT"

        return "SUSPICIOUS"

    # =====================================================
    # DRAWDOWN
    # =====================================================

    def _classify_drawdown(
        self,
        pnl: float,
        drawdown: float
    ) -> str:

        if pnl <= 0:
            return "CRITICAL"

        ratio = (
            drawdown / pnl
        )

        if ratio > 0.50:
            return "HIGH"

        if ratio > 0.30:
            return "MODERATE"

        if ratio > 0.15:
            return "LOW"

        return "VERY_LOW"

    # =====================================================
    # SAMPLE SIZE
    # =====================================================

    def _classify_sample_size(
        self,
        trades: int
    ) -> str:

        if trades < 100:
            return "LOW_SAMPLE"

        if trades < 300:
            return "MODERATE_SAMPLE"

        return "STATISTICALLY_RELEVANT"

    # =====================================================
    # RISK / REWARD
    # =====================================================

    def _classify_risk_reward(
        self,
        value: float
    ) -> str:

        if value < 1:
            return "POOR"

        if value < 1.5:
            return "AVERAGE"

        if value < 2:
            return "GOOD"

        return "EXCELLENT"

    # =====================================================
    # OVERFIT DETECTION
    # =====================================================

    def _detect_overfit(
        self,
        winrate: float,
        profit_factor: float,
        pnl: float,
        drawdown: float,
        trades: int
    ) -> str:

        if (
            profit_factor > 5
            and winrate > 0.80
            and drawdown < (
                pnl * 0.05
            )
            and trades < 100
        ):
            return "HIGH"

        if (
            profit_factor > 3
            and winrate > 0.70
        ):
            return "MODERATE"

        return "LOW"

    # =====================================================
    # ROBUSTNESS
    # =====================================================

    def _calculate_robustness(
        self,
        winrate: float,
        profit_factor: float,
        drawdown: float,
        trades: int
    ) -> str:

        score = 0

        if winrate > 0.55:
            score += 1

        if profit_factor > 1.5:
            score += 1

        if drawdown < 5000:
            score += 1

        if trades > 100:
            score += 1

        if score <= 1:
            return "WEAK"

        if score == 2:
            return "MODERATE"

        if score == 3:
            return "STRONG"

        return "INSTITUTIONAL"

    # =====================================================
    # FINAL VERDICT
    # =====================================================

    def _generate_verdict(
        self,
        overfit_risk: str,
        robustness: str,
        sample_rating: str
    ) -> Dict:

        if overfit_risk == "HIGH":

            return {

                "status": (
                    "PROMISING_BUT_SUSPICIOUS"
                ),

                "recommendation": (

                    "Run walk-forward validation "
                    "and validate on multiple "
                    "market regimes."
                )
            }

        if robustness in [
            "STRONG",
            "INSTITUTIONAL"
        ]:

            return {

                "status": (
                    "ROBUST"
                ),

                "recommendation": (

                    "System demonstrates "
                    "consistent statistical edge."
                )
            }

        if sample_rating == "LOW_SAMPLE":

            return {

                "status": (
                    "INSUFFICIENT_DATA"
                ),

                "recommendation": (

                    "Increase trade sample size "
                    "before drawing conclusions."
                )
            }

        return {

            "status": (
                "MODERATE"
            ),

            "recommendation": (

                "Continue validation and "
                "stress testing."
            )
        }


validation_interpreter = (
    ValidationInterpreter()
)
