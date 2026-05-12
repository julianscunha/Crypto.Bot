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
    market_structure_service
)

from colorama import (
    Fore,
    Style,
    init
)

from core.utils.console_logger import (
    log
)

init(autoreset=True)


class StrategyAgent:

    def __init__(self, bus):

        self.bus = bus

        self.signal_quality = (
            SignalQualityService()
        )

        self.market_structure = (
            market_structure_service
        )

        self.bus.subscribe(self)

    async def on_message(self, message):

        if not isinstance(
            message,
            MarketAnalysisMessage
        ):
            return

        payload = message.payload
        
        log(
            "STRATEGY",
            f"{payload.symbol}",
            Fore.CYAN
        )

        candles_count = len(
            self.market_structure.get_prices(
                payload.user_id,
                payload.symbol
            )
        )
        
        log(
            "STRUCTURE DATA",
            f"{payload.symbol} candles={candles_count}",
            Fore.LIGHTMAGENTA_EX
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

        structure_valid = (
            structure["valid"]
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
            
            log(
                "SIGNAL BLOCKED",
                f"{payload.symbol} | {reason}",
                Fore.LIGHTRED_EX
            )

            return

        # =====================================================
        # FINAL STRUCTURE BLOCK
        # =====================================================
        
        # TODO:
        # Reativar market structure validation
        # após dataset real e tuning estrutural

      # if not structure_valid:
      #
      #     print(
      #         Fore.LIGHTYELLOW_EX +
      #         "[STRUCTURE BLOCKED]" +
      #         Style.RESET_ALL +
      #         f" {payload.symbol} "
      #         f"| {structure['reason']}"
      #     )
      #
      #     return
        
        log(
            "SIGNAL",
            f"{payload.symbol} strength={signal_strength}",
            Fore.LIGHTGREEN_EX
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