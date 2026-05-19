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

from core.config.trade_management_config import (
    TRADE_MANAGEMENT_CONFIG
)

from core.config.exchange_config import (
    EXCHANGE_CONFIG
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

        self.trading_config = (
            TRADING_CONFIG
        )

        self.management_config = (
            TRADE_MANAGEMENT_CONFIG
        )

        self.exchange_config = (
            EXCHANGE_CONFIG
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
        # SIGNAL VALIDATION
        # =================================================

        valid, reason = (
            self._validate_signal(
                payload
            )
        )

        if not valid:

            log(
                "RISK",
                f"BLOCKED {reason}",
                "WARNING"
            )

            return

        # =================================================
        # PRICING
        # =================================================

        entry_price = round(

            payload.entry_price,

            self.exchange_config[
                "price_precision"
            ]
        )

        # =================================================
        # LEVELS
        # =================================================

        risk_levels = (
            self._calculate_risk_levels(
                payload,
                entry_price
            )
        )

        if not risk_levels:

            log(
                "RISK",
                "BLOCKED INVALID_RISK_LEVELS",
                "ERROR"
            )

            return

        stop_loss = (
            risk_levels["stop_loss"]
        )

        take_profit = (
            risk_levels["take_profit"]
        )

        trailing_stop = (
            risk_levels["trailing_stop"]
        )

        risk_distance = (
            risk_levels["risk_distance"]
        )

        reward_distance = (
            risk_levels["reward_distance"]
        )

        # =================================================
        # POSITION SIZE
        # =================================================

        quantity = (
            self._calculate_position_size(
                entry_price,
                risk_distance
            )
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

        quantity = (
            self._apply_exposure_limit(
                entry_price,
                quantity
            )
        )

        if quantity <= 0:

            log(
                "RISK",
                "BLOCKED EXPOSURE_LIMIT",
                "WARNING"
            )

            return

        # =================================================
        # RISK REWARD
        # =================================================

        risk_reward_ratio = round(

            reward_distance
            / risk_distance,

            2
        )

        minimum_rr = (
            self.trading_config[
                "minimum_risk_reward_ratio"
            ]
        )

        if risk_reward_ratio < minimum_rr:

            log(
                "RISK",
                (
                    f"BLOCKED LOW_RR "
                    f"rr={risk_reward_ratio}"
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

                risk_reward=risk_reward_ratio
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
                f"rr={risk_reward_ratio} "
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

    # =====================================================
    # SIGNAL VALIDATION
    # =====================================================

    def _validate_signal(
        self,
        payload
    ):

        # =================================================
        # ATR
        # =================================================

        if payload.atr is None:

            return (
                False,
                "ATR_NOT_READY"
            )

        if payload.atr <= 0:

            return (
                False,
                "INVALID_ATR"
            )

        # =================================================
        # SIGNAL
        # =================================================

        if payload.signal != "BUY":

            return (
                False,
                "INVALID_SIGNAL"
            )

        # =================================================
        # POSITION
        # =================================================

        existing_position = (

            self.positions
            .get_open_trade(

                user_id=payload.user_id,

                symbol=payload.symbol
            )
        )

        if existing_position:

            return (
                False,
                "POSITION_ALREADY_OPEN"
            )

        # =================================================
        # ENTRY
        # =================================================

        if payload.entry_price <= 0:

            return (
                False,
                "INVALID_ENTRY"
            )

        return (
            True,
            "VALID"
        )

    # =====================================================
    # RISK LEVELS
    # =====================================================

    def _calculate_risk_levels(
        self,
        payload,
        entry_price: float
    ):

        atr_stop_multiplier = (
            self.trading_config[
                "atr_stop_multiplier"
            ]
        )

        atr_take_profit_multiplier = (
            self.trading_config[
                "atr_take_profit_multiplier"
            ]
        )

        atr_trailing_multiplier = (
            self.management_config[
                "atr_trailing_multiplier"
            ]
        )

        precision = (
            self.exchange_config[
                "price_precision"
            ]
        )

        stop_loss = round(

            entry_price

            - (

                payload.atr
                *
                atr_stop_multiplier
            ),

            precision
        )

        take_profit = round(

            entry_price

            + (

                payload.atr
                *
                atr_take_profit_multiplier
            ),

            precision
        )

        trailing_stop = round(

            payload.atr
            *
            atr_trailing_multiplier,

            precision
        )

        # =================================================
        # VALIDATION
        # =================================================

        if stop_loss <= 0:

            return None

        if stop_loss >= entry_price:

            return None

        if take_profit <= entry_price:

            return None

        risk_distance = round(

            abs(
                entry_price
                -
                stop_loss
            ),

            precision
        )

        reward_distance = round(

            take_profit
            -
            entry_price,

            precision
        )

        if risk_distance <= 0:

            return None

        return {

            "stop_loss":
                stop_loss,

            "take_profit":
                take_profit,

            "trailing_stop":
                trailing_stop,

            "risk_distance":
                risk_distance,

            "reward_distance":
                reward_distance
        }

    # =====================================================
    # POSITION SIZE
    # =====================================================

    def _calculate_position_size(
        self,
        entry_price: float,
        risk_distance: float
    ):

        account_balance = (
            self.trading_config[
                "account_balance"
            ]
        )

        risk_percent = (
            self.trading_config[
                "risk_per_trade_percent"
            ]
        )

        quantity_precision = (
            self.exchange_config[
                "quantity_precision"
            ]
        )

        risk_amount = (

            account_balance

            * (
                risk_percent / 100
            )
        )

        quantity = round(

            risk_amount
            / risk_distance,

            quantity_precision
        )

        return max(
            quantity,
            0.0
        )

    # =====================================================
    # EXPOSURE LIMIT
    # =====================================================

    def _apply_exposure_limit(
        self,
        entry_price: float,
        quantity: float
    ):

        account_balance = (
            self.trading_config[
                "account_balance"
            ]
        )

        max_exposure_percent = (
            self.trading_config[
                "max_position_exposure_percent"
            ]
        )

        quantity_precision = (
            self.exchange_config[
                "quantity_precision"
            ]
        )

        maximum_position_value = (

            account_balance

            * (
                max_exposure_percent / 100
            )
        )

        position_notional = (
            quantity
            * entry_price
        )

        if position_notional <= maximum_position_value:

            return quantity

        adjusted_quantity = round(

            maximum_position_value
            / entry_price,

            quantity_precision
        )

        return max(
            adjusted_quantity,
            0.0
        )