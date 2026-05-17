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

from core.utils.console_logger import (
    log,
    print_section
)

from backtest.reports.report_renderer import (
    ReportRenderer
)

from core.services.portfolio_service import (
    PortfolioService
)

from core.config.trading_config import (
    TRADING_CONFIG
)

from core.config.settings import (
    settings
)

from core.state.market_state import (
    market_state
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

    print_section(
        "CRYPTO.BOT ENGINE"
    )

    log(
        "SYSTEM",
        (
            f"MODE           "
            f"{settings.MODE.upper()}"
        )
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
        (
            f"TIMEFRAME      "
            f"{settings.KLINE_INTERVAL}"
        )
    )

    log(
        "SYSTEM",
        "DATABASE       CONNECTED",
        "SUCCESS"
    )

    # =====================================================
    # EVENT BUS
    # =====================================================

    bus = EventBus()

    log(
        "SYSTEM",
        "EVENT BUS      READY",
        "SUCCESS"
    )

    # =====================================================
    # AGENTS
    # =====================================================

    AnalystAgent(bus)

    StrategyAgent(bus)

    RiskAgent(bus)

    ExecutionAgent(bus)

    PositionManagerAgent(bus)

    log(
        "SYSTEM",
        "AGENTS         READY",
        "SUCCESS"
    )

    # =====================================================
    # WEBSOCKET
    # =====================================================

    ws = BinanceWS(
        bus=bus,
        user_id=0
    )

    await ws.start()


# =========================================================
# SESSION REPORT
# =========================================================

def print_session_report():

    portfolio_service = (
        PortfolioService()
    )

    snapshot = (
        portfolio_service.build_snapshot(
            user_id=0,
            initial_balance=(
                TRADING_CONFIG[
                    "account_balance"
                ]
            )
        )
    )

    ReportRenderer.print_header(
        "LIVE SESSION REPORT"
    )

    # =====================================================
    # SESSION
    # =====================================================

    ReportRenderer.print_section(
        "SESSION"
    )

    ReportRenderer.print_metric(
        "Balance",
        snapshot.balance
    )

    ReportRenderer.print_metric(
        "Equity",
        snapshot.equity
    )

    ReportRenderer.print_metric(
        "Realized PnL",
        snapshot.realized_pnl
    )

    ReportRenderer.print_metric(
        "Unrealized PnL",
        snapshot.unrealized_pnl
    )

    ReportRenderer.print_metric(
        "Total PnL",
        snapshot.total_pnl
    )

    ReportRenderer.print_metric(
        "Open Positions",
        snapshot.open_positions
    )

    ReportRenderer.print_metric(
        "Closed Positions",
        snapshot.closed_positions
    )

    ReportRenderer.print_metric(
        "Exposure",
        snapshot.exposure
    )

    ReportRenderer.print_metric(
        "Drawdown",
        f"{snapshot.drawdown}%"
    )

    # =====================================================
    # BLOCKED SIGNALS
    # =====================================================

    blocked = (
        market_state.get_blocked_signals()
    )

    if blocked:

        ReportRenderer.print_section(
            "BLOCKED SIGNALS"
        )

        for reason, count in blocked.items():

            ReportRenderer.print_metric(
                reason,
                count
            )

    # =====================================================
    # MARKET
    # =====================================================

    market_snapshot = (
        market_state.snapshot()
    )

    ReportRenderer.print_section(
        "MARKET"
    )

    ReportRenderer.print_metric(
        "Generated Signals",
        market_snapshot[
            "generated_signals"
        ]
    )

    ReportRenderer.print_metric(
        "Acceptance Ratio",
        (
            f"{market_snapshot['acceptance_ratio']}%"
        )
    )

    ReportRenderer.print_metric(
        "Messages",
        market_snapshot[
            "total_messages"
        ]
    )

    ReportRenderer.print_metric(
        "Websocket",
        (
            "CONNECTED"
            if market_snapshot[
                "websocket_connected"
            ]
            else "DISCONNECTED"
        )
    )

    ReportRenderer.print_metric(
        "Active Symbols",
        len(
            market_snapshot[
                "active_symbols"
            ]
        )
    )

    ReportRenderer.print_metric(
        "Uptime (sec)",
        market_snapshot[
            "uptime_seconds"
        ]
    )

    print()


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print_session_report()