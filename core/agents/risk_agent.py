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

from colorama import (
    Fore,
    Style,
    init
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
        
        if payload.atr is None:

            log(
                "RISK BLOCKED",
                f"{payload.symbol} | ATR_MISSING",
                Fore.RED
            )
        
            return
        
        log(
            "RISK",
            f"{payload.symbol}",
            Fore.LIGHTYELLOW_EX
        )

        # =====================================================
        # SIGNAL FILTER
        # =====================================================

        if payload.signal != "BUY":
           
            log(
                "RISK BLOCKED",
                f"{payload.symbol} | INVALID_SIGNAL",
                Fore.LIGHTRED_EX
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
                "RISK BLOCKED",
                f"{payload.symbol} | POSITION_ALREADY_OPEN",
                Fore.LIGHTRED_EX
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
        # PAYLOAD
        # =====================================================

        risk_distance = (
            entry_price - stop_loss
        )
        
        if risk_distance <= 0:

            log(
                "RISK BLOCKED",
                f"{payload.symbol} | INVALID_RISK_DISTANCE",
                Fore.RED
            )
        
            return
        
        reward_distance = (
            take_profit - entry_price
        )
        
        risk_reward = round(
            reward_distance / risk_distance,
            2
        )
        
        log(
            "ATR RISK",
            (
                f"{payload.symbol} "
                f"ATR={payload.atr:.4f}"
                f"SL={stop_loss} "
                f"TP={take_profit}"
            ),
            Fore.LIGHTCYAN_EX
        )
        
        
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
        # PUBLISH
        # =====================================================
        
        log(
                "RISK APPROVED",
                f"{payload.symbol}",
                Fore.LIGHTGREEN_EX
            )

        await self.bus.publish(
            decision_message
        )