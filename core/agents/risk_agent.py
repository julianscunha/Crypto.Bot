# -*- coding: utf-8 -*-

from core.contracts.messages import (
    StrategySignalMessage,
    RiskDecisionMessage,
    RiskDecisionPayload
)

from data.storage.repositories.trades_repository import (
    trades_repository
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.utils.console_logger import (
    log
)


class RiskAgent:

    def __init__(self, bus):

        self.bus = bus

        self.positions = trades_repository

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            StrategySignalMessage
        ):
            return

        payload = message.payload

        # =====================================================
        # START VALIDATION
        # =====================================================

        log(
            "RISK",
            f"VALIDATING {payload.symbol}"
        )

        # =====================================================
        # ATR VALIDATION
        # =====================================================

        if payload.atr is None:

            log(
                "RISK",
                f"BLOCKED {payload.symbol} | ATR_MISSING",
                "ERROR"
            )

            return

        # =====================================================
        # SIGNAL FILTER
        # =====================================================

        if payload.signal != "BUY":

            log(
                "RISK",
                (
                    f"BLOCKED "
                    f"{payload.symbol} "
                    f"| INVALID_SIGNAL"
                ),
                "ERROR"
            )

            return

        # =====================================================
        # EXISTING POSITION
        # =====================================================

        existing_position = (
            self.positions.get_open_trade(
                user_id=payload.user_id,
                symbol=payload.symbol
            )
        )

        if existing_position:

            log(
                "RISK",
                (
                    f"BLOCKED "
                    f"{payload.symbol} "
                    f"| POSITION_ALREADY_OPEN"
                ),
                "ERROR"
            )

            return

        # =====================================================
        # RISK CALCULATION
        # =====================================================

        entry_price = payload.entry_price

        stop_loss = round(
            entry_price - (
                payload.atr * TRADING_CONFIG[
                    "atr_stop_multiplier"
                ]
            ),
            2
        )

        take_profit = round(
            entry_price + (
                payload.atr * TRADING_CONFIG[
                    "atr_take_profit_multiplier"
                ]
            ),
            2
        )

        trailing_stop = round(
            payload.atr * TRADING_CONFIG[
                "atr_trailing_multiplier"
            ],
            2
        )

        quantity = (
            TRADING_CONFIG[
                "default_quantity"
            ]
        )

        # =====================================================
        # RISK / REWARD
        # =====================================================

        risk_distance = (
            entry_price - stop_loss
        )

        if risk_distance <= 0:

            log(
                "RISK",
                (
                    f"BLOCKED "
                    f"{payload.symbol} "
                    f"| INVALID_RISK_DISTANCE"
                ),
                "ERROR"
            )

            return

        reward_distance = (
            take_profit - entry_price
        )

        risk_reward = round(
            reward_distance / risk_distance,
            2
        )

        # =====================================================
        # ATR INFO
        # =====================================================

        log(
            "RISK",
            (
                f"ATR "
                f"{payload.symbol} "
                f"atr={payload.atr:.4f} "
                f"sl={stop_loss} "
                f"tp={take_profit}"
            )
        )

        # =====================================================
        # PAYLOAD
        # =====================================================

        decision_payload = (
            RiskDecisionPayload(
                user_id=payload.user_id,
                symbol=payload.symbol,
                signal=payload.signal,
                entry_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                risk_reward=risk_reward
            )
        )

        decision_message = (
            RiskDecisionMessage(
                sender="RiskAgent",
                payload=decision_payload
            )
        )

        # =====================================================
        # APPROVED
        # =====================================================

        log(
            "RISK",
            (
                f"APPROVED "
                f"{payload.symbol} "
                f"rr={risk_reward}"
            ),
            "SUCCESS"
        )

        # =====================================================
        # PUBLISH
        # =====================================================

        await self.bus.publish(
            decision_message
        )