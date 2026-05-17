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

    def __init__(
        self,
        bus
    ):

        self.bus = bus

        self.positions = (
            trades_repository
        )

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
            StrategySignalMessage
        ):

            return

        payload = (
            message.payload
        )

        # =================================================
        # ATR VALIDATION
        # =================================================

        if payload.atr is None:

            log(
                "RISK",
                "BLOCKED ATR_NOT_READY",
                "WARNING"
            )

            return

        if payload.atr <= 0:

            log(
                "RISK",
                "BLOCKED INVALID_ATR",
                "ERROR"
            )

            return

        # =================================================
        # SIGNAL FILTER
        # =================================================

        if payload.signal != "BUY":

            log(
                "RISK",
                "BLOCKED INVALID_SIGNAL",
                "WARNING"
            )

            return

        # =================================================
        # EXISTING POSITION
        # =================================================

        existing_position = (

            self.positions.get_open_trade(

                user_id=payload.user_id,

                symbol=payload.symbol
            )
        )

        if existing_position:

            log(
                "RISK",
                "BLOCKED POSITION_ALREADY_OPEN",
                "WARNING"
            )

            return

        # =================================================
        # ENTRY
        # =================================================

        entry_price = round(
            payload.entry_price,
            2
        )

        if entry_price <= 0:

            log(
                "RISK",
                "BLOCKED INVALID_ENTRY",
                "ERROR"
            )

            return

        # =================================================
        # ATR CONFIG
        # =================================================

        atr_stop_multiplier = (

            TRADING_CONFIG[
                "atr_stop_multiplier"
            ]
        )

        atr_take_profit_multiplier = (

            TRADING_CONFIG[
                "atr_take_profit_multiplier"
            ]
        )

        atr_trailing_multiplier = (

            TRADING_CONFIG[
                "atr_trailing_multiplier"
            ]
        )

        # =================================================
        # LEVELS
        # =================================================

        stop_loss = round(

            entry_price
            -
            (
                payload.atr
                *
                atr_stop_multiplier
            ),

            2
        )

        take_profit = round(

            entry_price
            +
            (
                payload.atr
                *
                atr_take_profit_multiplier
            ),

            2
        )

        trailing_stop = round(

            payload.atr
            *
            atr_trailing_multiplier,

            2
        )

        # =================================================
        # STOP VALIDATION
        # =================================================

        if stop_loss <= 0:

            log(
                "RISK",
                "BLOCKED INVALID_STOP",
                "ERROR"
            )

            return

        if stop_loss >= entry_price:

            log(
                "RISK",
                "BLOCKED INVALID_STOP",
                "ERROR"
            )

            return

        if take_profit <= entry_price:

            log(
                "RISK",
                "BLOCKED INVALID_TARGET",
                "ERROR"
            )

            return

        # =================================================
        # RISK DISTANCE
        # =================================================

        risk_distance = round(

            abs(
                entry_price - stop_loss
            ),

            8
        )

        if risk_distance <= 0:

            log(
                "RISK",
                "BLOCKED INVALID_RISK_DISTANCE",
                "ERROR"
            )

            return

        # =================================================
        # ACCOUNT
        # =================================================

        account_balance = (

            TRADING_CONFIG[
                "account_balance"
            ]
        )

        risk_percent = (

            TRADING_CONFIG[
                "risk_per_trade_percent"
            ]
        )

        risk_amount = round(

            account_balance
            *
            (
                risk_percent / 100
            ),

            2
        )

        # =================================================
        # POSITION SIZE
        # =================================================

        quantity = round(

            risk_amount
            / risk_distance,

            6
        )

        if quantity <= 0:

            log(
                "RISK",
                "BLOCKED INVALID_POSITION_SIZE",
                "ERROR"
            )

            return

        # =================================================
        # EXPOSURE
        # =================================================

        notional_value = round(

            quantity
            *
            entry_price,

            2
        )

        max_exposure_percent = (

            TRADING_CONFIG[
                "max_position_exposure_percent"
            ]
        )

        max_exposure_value = round(

            account_balance
            *
            (
                max_exposure_percent / 100
            ),

            2
        )

        # =================================================
        # MICRO ACCOUNT ADAPTATION
        # =================================================

        if notional_value > max_exposure_value:

            quantity = round(

                max_exposure_value
                / entry_price,

                6
            )

            notional_value = round(

                quantity
                *
                entry_price,

                2
            )

        # =================================================
        # FINAL VALIDATION
        # =================================================

        if quantity <= 0:

            log(
                "RISK",
                "BLOCKED EXPOSURE_LIMIT",
                "WARNING"
            )

            return

        # =================================================
        # REWARD
        # =================================================

        reward_distance = round(

            take_profit
            - entry_price,

            8
        )

        risk_reward = round(

            reward_distance
            / risk_distance,

            2
        )

        # =================================================
        # RR FILTER
        # =================================================

        if risk_reward < 1.2:

            log(
                "RISK",
                (
                    f"BLOCKED LOW_RR "
                    f"rr={risk_reward}"
                ),
                "WARNING"
            )

            return

        # =================================================
        # PAYLOAD
        # =================================================

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

        # =================================================
        # APPROVED
        # =================================================

        log(
            "RISK",
            (
                f"APPROVED "
                f"rr={risk_reward} "
                f"qty={quantity}"
            ),
            "SUCCESS"
        )

        # =================================================
        # PUBLISH
        # =================================================

        await self.bus.publish(
            decision_message
        )