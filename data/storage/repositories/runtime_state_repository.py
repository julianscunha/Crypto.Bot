# -*- coding: utf-8 -*-

"""
Persists MarketState telemetry across OS process boundaries.

apps/trader/runner.py and apps/api/main.py run as separate
subprocesses under Full Stack (see scripts/bootstrap/launcher.py).
core.state.market_state.MarketState is an in-memory singleton, so
writes made in the Runner process (websocket_connected,
active_symbols, signal counters) are invisible to the API process.
This repository is the shared, cross-process source of truth: the
Runner periodically flushes its in-memory MarketState here, and the
API reads from here instead of its own (always-empty) in-memory copy.

Always a single row (id=1), upserted -- this is live telemetry, not
a history to query over time (EquityCurve/PortfolioSnapshot already
serve that purpose for portfolio data).
"""

import json

from sqlalchemy.orm import (
    Session
)

from data.storage.database import (
    SessionLocal
)

from data.storage.models import (
    RuntimeState
)


RUNTIME_STATE_ID = 1


class RuntimeStateRepository:

    def __init__(self):

        pass

    # =====================================================
    # SESSION
    # =====================================================

    def _session(
        self
    ) -> Session:

        return SessionLocal()

    # =====================================================
    # UPSERT FROM SNAPSHOT
    # =====================================================

    def upsert(
        self,
        snapshot: dict
    ):

        """
        snapshot is the dict returned by MarketState.snapshot().
        Writes (or overwrites) the single runtime_state row with it.
        """

        session = self._session()

        try:

            row = (

                session.get(
                    RuntimeState,
                    RUNTIME_STATE_ID
                )
            )

            if row is None:

                row = RuntimeState(
                    id=RUNTIME_STATE_ID
                )

                session.add(
                    row
                )

            row.started_at = (
                snapshot.get("started_at")
            )

            row.websocket_connected = bool(
                snapshot.get(
                    "websocket_connected",
                    False
                )
            )

            row.total_market_messages = int(
                snapshot.get(
                    "total_market_messages",
                    0
                )
            )

            row.last_market_message_at = (
                snapshot.get(
                    "last_market_message_at"
                )
            )

            row.active_symbols_json = json.dumps(
                sorted(
                    snapshot.get(
                        "active_symbols",
                        []
                    )
                )
            )

            row.total_analysis_requests = int(
                snapshot.get(
                    "total_analysis_requests",
                    0
                )
            )

            row.total_generated_signals = int(
                snapshot.get(
                    "total_generated_signals",
                    0
                )
            )

            row.total_approved_signals = int(
                snapshot.get(
                    "total_approved_signals",
                    0
                )
            )

            row.total_rejected_signals = int(
                snapshot.get(
                    "total_rejected_signals",
                    0
                )
            )

            row.total_executed_orders = int(
                snapshot.get(
                    "total_executed_orders",
                    0
                )
            )

            row.total_closed_positions = int(
                snapshot.get(
                    "total_closed_positions",
                    0
                )
            )

            row.blocked_signal_reasons_json = json.dumps(
                snapshot.get(
                    "blocked_signal_reasons",
                    {}
                )
            )

            row.execution_reasons_json = json.dumps(
                snapshot.get(
                    "execution_reasons",
                    {}
                )
            )

            session.commit()

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    # =====================================================
    # GET
    # =====================================================

    def get(
        self
    ):

        """
        Returns the persisted runtime state as a plain dict shaped
        like MarketState.snapshot(), or None if the Runner process
        has never flushed yet (e.g. API started without a Runner).
        """

        session = self._session()

        try:

            row = (

                session.get(
                    RuntimeState,
                    RUNTIME_STATE_ID
                )
            )

            if row is None:

                return None

            return {
                "started_at":
                    row.started_at,

                "websocket_connected":
                    row.websocket_connected,

                "total_market_messages":
                    row.total_market_messages,

                "last_market_message_at":
                    row.last_market_message_at,

                "active_symbols": json.loads(
                    row.active_symbols_json
                    or "[]"
                ),

                "total_analysis_requests":
                    row.total_analysis_requests,

                "total_generated_signals":
                    row.total_generated_signals,

                "total_approved_signals":
                    row.total_approved_signals,

                "total_rejected_signals":
                    row.total_rejected_signals,

                "total_executed_orders":
                    row.total_executed_orders,

                "total_closed_positions":
                    row.total_closed_positions,

                "blocked_signal_reasons": json.loads(
                    row.blocked_signal_reasons_json
                    or "{}"
                ),

                "execution_reasons": json.loads(
                    row.execution_reasons_json
                    or "{}"
                ),

                "updated_at":
                    row.updated_at
            }

        finally:

            session.close()

    # =====================================================
    # RESET
    # =====================================================

    def reset(
        self
    ):

        session = self._session()

        try:

            session.query(
                RuntimeState
            ).delete()

            session.commit()

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()


runtime_state_repository = (
    RuntimeStateRepository()
)
