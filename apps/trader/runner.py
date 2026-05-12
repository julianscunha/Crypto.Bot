import asyncio

from core.bus.event_bus import EventBus

from core.agents.analyst_agent import AnalystAgent

from core.agents.strategy_agent import StrategyAgent

from core.agents.risk_agent import RiskAgent

from core.agents.execution_agent import ExecutionAgent

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

from services.market_regime_service import (
    market_regime_service
)

from core.contracts.messages import (
    MarketDataMessage
)

from core.config.regime_config_loader import (
    regime_config_loader
)

from colorama import (
    Fore,
    Style
)

from core.utils.console_logger import (
    log
)

DEFAULT_USER_ID = 0

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT"
]


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
            "MARKET REGIME",
            f"{payload.symbol} {regime}",
            Fore.LIGHTBLUE_EX
        )
        
        regime_config_loader.load_regime(
            regime
        )


async def main():

    init_db()

    load_best_config()

    bus = EventBus()

    AnalystAgent(bus)

    StrategyAgent(bus)

    RiskAgent(bus)

    ExecutionAgent(bus)

    PositionManagerAgent(bus)

    MarketRegimeLogger(bus)

    ws = BinanceWS(
        bus=bus,
        user_id=DEFAULT_USER_ID
    )

    await ws.start()


if __name__ == "__main__":

    asyncio.run(main())