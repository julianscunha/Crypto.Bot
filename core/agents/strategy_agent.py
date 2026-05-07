# -*- coding: utf-8 -*-

from core.contracts.messages import (
    MarketAnalysisMessage,
    StrategySignalMessage,
    StrategySignalPayload
)

from core.services.signal_quality_service import (
    SignalQualityService
)

from core.services.market_structure_service import (
    MarketStructureService
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

        self.market_structure = (
            MarketStructureService()
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
        # UPDATE STRUCTURE ENGINE
        # =====================================================

        self.market_structure.update_market_data(
            user_id=payload.user_id,
            symbol=payload.symbol,
            price=payload.reference_price
        )

        candles_count = len(
            self.market_structure.get_prices(
                payload.user_id,
                payload.symbol
            )
        )

        print(
            Fore.MAGENTA +
            f"[STRUCTURE DATA] "
            f"{payload.symbol} "
            f"candles={candles_count}" +
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
        # MARKET STRUCTURE VALIDATION
        # =====================================================

        structure = (
            self.market_structure
            .analyze_structure(
                user_id=payload.user_id,
                symbol=payload.symbol
            )
        )

        if not structure["valid"]:

            print(
                Fore.YELLOW +
                f"[STRUCTURE BLOCKED] "
                f"{payload.symbol} "
                f"| {structure['reason']}" +
                Style.RESET_ALL
            )

            return

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