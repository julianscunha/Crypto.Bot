# -*- coding: utf-8 -*-

import asyncio

from core.bus.event_bus import (
    EventBus
)

from core.agents.analyst_agent import (
    AnalystAgent
)

from core.agents.strategy_agent import (
    StrategyAgent
)

from core.agents.risk_agent import (
    RiskAgent
)

from core.agents.execution_agent import (
    ExecutionAgent
)

from core.agents.position_manager_agent import (
    PositionManagerAgent
)

from data.ingestion.binance_ws import (
    BinanceWS
)

from data.storage.database import (
    init_db
)

from core.config.config_loader import (
    load_best_config
)

from core.services.market_regime_service import (
    market_regime_service
)

from core.contracts.messages import (
    MarketDataMessage
)

from core.config.regime_config_loader import (
    regime_config_loader
)

from core.utils.console_logger import (
    log
)

from core.config.settings import (
    settings
)


class MarketRegimeLogger:

    def __init__(self, bus):

        bus.subscribe(self)

    async def on_message(
        self,
        message
    ):

        if not isinstance(
            message,
            MarketDataMessage
        ):
            return

        payload = message.payload

        market_regime_service.update_price(
            symbol=payload.symbol,
            close=payload.close
        )

        regime = (
            market_regime_service
            .detect_regime(
                payload.symbol
            )
        )

        log(
            "MARKET",
            (
                f"REGIME "
                f"{payload.symbol} "
                f"{regime}"
            )
        )

        regime_config_loader.load_regime(
            regime
        )


async def main():

    # =====================================================
    # DATABASE
    # =====================================================

    init_db()

    # =====================================================
    # CONFIG
    # =====================================================

    load_best_config()

    # =====================================================
    # SYSTEM PANEL
    # =====================================================

    log(
        "SYSTEM",
        (
            f"MODE           "
            f"{settings.MODE.upper()}"
        ),
    )

    log(
        "SYSTEM",
        (
            "SYMBOLS        "
            f"{' '.join(settings.SYMBOLS)}"
        )
    )

    log(
        "SYSTEM",
        "TIMEFRAME      1m"
    )

    log(
        "SYSTEM",
        "DATABASE       CONNECTED",
    )

    # =====================================================
    # EVENT BUS
    # =====================================================

    bus = EventBus()

    log(
        "SYSTEM",
        "EVENT BUS      READY",
    )

    # =====================================================
    # AGENTS
    # =====================================================

    AnalystAgent(bus)

    StrategyAgent(bus)

    RiskAgent(bus)

    ExecutionAgent(bus)

    PositionManagerAgent(bus)

    MarketRegimeLogger(bus)

    log(
        "SYSTEM",
        "AGENTS         READY",
    )

    # =====================================================
    # WEBSOCKET
    # =====================================================

    ws = BinanceWS(
        bus=bus,
        user_id=0
    )

    await ws.start()


if __name__ == "__main__":

    try:

        asyncio.run(main())
    
    except KeyboardInterrupt:
    
        print()
    
        print("=" * 60)
        print("                LIVE SESSION REPORT")
        print("=" * 60)
    
        from core.metrics.metrics_service import (
            metrics_service
        )
    
        metrics = (
            metrics_service.calculate()
        )
    
        print()
        print(
            f"Trades ...................... "
            f"{metrics['total_trades']}"
        )
    
        print(
            f"Winrate .................... "
            f"{metrics['winrate']:.2%}"
        )
    
        print(
            f"PnL ......................... "
            f"{metrics['pnl']:.2f}"
        )
    
        print(
            f"Profit Factor .............. "
            f"{metrics['profit_factor']:.2f}"
        )
    
        print(
            f"Max Drawdown ............... "
            f"{metrics['max_drawdown']:.2f}"
        )
    
        print()
    
        print("=" * 60)
        print("                 ENGINE STOPPED")
        print("=" * 60)
    
    except Exception as error:
    
        print(
            f"[FATAL ERROR] {error}"
        )