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
            "[STRATEGY]" +
            Style.RESET_ALL +
            f" {payload.symbol}"
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
            Fore.LIGHTMAGENTA_EX +
            "[STRUCTURE DATA]" +
            Style.RESET_ALL +
            f" {payload.symbol} "
            f"candles={candles_count}"
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
                Fore.LIGHTYELLOW_EX +
                "[STRUCTURE BLOCKED]" +
                Style.RESET_ALL +
                f" {payload.symbol} "
                f"| {structure['reason']}"
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
                Fore.LIGHTRED_EX +
                "[SIGNAL BLOCKED]" +
                Style.RESET_ALL +
                f" {payload.symbol} "
                f"| {reason}"
            )

            return

        print(
            Fore.LIGHTGREEN_EX +
            "[SIGNAL]" +
            Style.RESET_ALL +
            f" {payload.symbol} "
            f"strength={signal_strength}"
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