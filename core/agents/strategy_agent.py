# -*- coding: utf-8 -*-

from core.contracts.messages import (
    MarketAnalysisMessage,
    StrategySignalMessage,
    StrategySignalPayload
)

from core.services.signal_quality_service import (
    SignalQualityService
)

from colorama import (
    Fore,
    Style,
    init
)

init(autoreset=True)


class StrategyAgent:

    def __init__(self, bus):

        self.bus = bus

        self.signal_quality = (
            SignalQualityService()
        )

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            MarketAnalysisMessage
        ):
            return

        payload = message.payload

        print(
            Fore.CYAN +
            f"[STRATEGY] "
            f"{payload.symbol}" +
            Style.RESET_ALL
        )

        # =====================================================
        # SIMPLE STRATEGY
        # =====================================================

        signal = "BUY"

        signal_strength = getattr(
            payload,
            "confidence",
            0.50
        )

        signal_payload = (
            StrategySignalPayload(
                user_id=payload.user_id,
                symbol=payload.symbol,
                signal=signal,
                entry_price=payload.reference_price,
                signal_strength=signal_strength
            )
        )

        # =====================================================
        # SIGNAL QUALITY VALIDATION
        # =====================================================

        valid, reason = (
            self.signal_quality.validate(
                signal_payload
            )
        )

        if not valid:
        
            print(
                Fore.RED +
                f"[SIGNAL BLOCKED] "
                f"{payload.symbol} "
                f"| {reason}" +
                Style.RESET_ALL
            )
        
            return
            print(
                Fore.GREEN +
                f"[SIGNAL] "
                f"{payload.symbol} "
                f"strength={signal_strength}" +
                Style.RESET_ALL
            )
        # =====================================================
        # PUBLISH
        # =====================================================

        signal_message = (
            StrategySignalMessage(
                sender="StrategyAgent",
                payload=signal_payload
            )
        )

        await self.bus.publish(
            signal_message
        )
        
        