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


# =========================================================
# SYSTEM PANEL
# =========================================================

def print_system_panel():

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

    log(
        "SYSTEM",
        "EVENT BUS      READY",
        "SUCCESS"
    )

    log(
        "SYSTEM",
        "AGENTS         READY",
        "SUCCESS"
    )

# =========================================================
# AGENTS
# =========================================================

def initialize_agents(
    bus
):

    AnalystAgent(bus)

    StrategyAgent(bus)

    RiskAgent(bus)

    ExecutionAgent(bus)

    PositionManagerAgent(bus)

# =========================================================
# SESSION REPORT
# =========================================================

def print_session_report():

    portfolio_service = (
        PortfolioService()
    )

    portfolio_snapshot = (

        portfolio_service
        .build_snapshot(

            user_id=0,

            initial_balance=(
                TRADING_CONFIG[
                    "account_balance"
                ]
            )
        )
    )

    runtime_snapshot = (
        market_state.snapshot()
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
        portfolio_snapshot.balance
    )

    ReportRenderer.print_metric(
        "Equity",
        portfolio_snapshot.equity
    )

    ReportRenderer.print_metric(
        "Realized PnL",
        portfolio_snapshot.realized_pnl
    )

    ReportRenderer.print_metric(
        "Unrealized PnL",
        portfolio_snapshot.unrealized_pnl
    )

    ReportRenderer.print_metric(
        "Total PnL",
        portfolio_snapshot.total_pnl
    )

    ReportRenderer.print_metric(
        "Open Positions",
        portfolio_snapshot.open_positions
    )

    ReportRenderer.print_metric(
        "Closed Positions",
        portfolio_snapshot.closed_positions
    )

    ReportRenderer.print_metric(
        "Exposure",
        portfolio_snapshot.exposure
    )

    ReportRenderer.print_metric(
        "Drawdown",
        f"{portfolio_snapshot.drawdown}%"
    )

    # =====================================================
    # BLOCKED SIGNALS
    # =====================================================

    blocked_reasons = (
        runtime_snapshot[
            "blocked_signal_reasons"
        ]
    )

    if blocked_reasons:

        ReportRenderer.print_section(
            "BLOCKED SIGNALS"
        )

        for reason, count in sorted(
            blocked_reasons.items(),
            key=lambda item: item[1],
            reverse=True
        ):

            ReportRenderer.print_metric(
                reason,
                count
            )

    # =====================================================
    # MARKET PIPELINE
    # =====================================================

    ReportRenderer.print_section(
        "MARKET"
    )

    ReportRenderer.print_metric(
        "Market Messages",
        runtime_snapshot[
            "total_market_messages"
        ]
    )

    ReportRenderer.print_metric(
        "Analysis Requests",
        runtime_snapshot[
            "total_analysis_requests"
        ]
    )

    ReportRenderer.print_metric(
        "Generated Signals",
        runtime_snapshot[
            "total_generated_signals"
        ]
    )

    ReportRenderer.print_metric(
        "Approved Signals",
        runtime_snapshot[
            "total_approved_signals"
        ]
    )

    ReportRenderer.print_metric(
        "Rejected Signals",
        runtime_snapshot[
            "total_rejected_signals"
        ]
    )

    ReportRenderer.print_metric(
        "Signal Generation Ratio",
        (
            f"{runtime_snapshot['signal_generation_ratio']}%"
        )
    )

    ReportRenderer.print_metric(
        "Signal Approval Ratio",
        (
            f"{runtime_snapshot['signal_approval_ratio']}%"
        )
    )

    ReportRenderer.print_metric(
        "Websocket",
        (
            "CONNECTED"
            if runtime_snapshot[
                "websocket_connected"
            ]
            else "DISCONNECTED"
        )
    )

    ReportRenderer.print_metric(
        "Active Symbols",
        len(
            runtime_snapshot[
                "active_symbols"
            ]
        )
    )

    ReportRenderer.print_metric(
        "Uptime (sec)",
        runtime_snapshot[
            "uptime_seconds"
        ]
    )

    ReportRenderer.print_footer()

    print()

# =========================================================
# MAIN
# =========================================================

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

    print_system_panel()

    # =====================================================
    # EVENT BUS
    # =====================================================

    bus = EventBus()

    # =====================================================
    # AGENTS
    # =====================================================

    initialize_agents(
        bus
    )

    # =====================================================
    # WEBSOCKET
    # =====================================================

    websocket = BinanceWS(

        bus=bus,

        user_id=0
    )

    await websocket.start()

# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        log(
            "SYSTEM",
            "Shutdown...................... OK",
            "WARNING"
        )

        print_session_report()