# scripts/repository_refactor.py

# -*- coding: utf-8 -*-

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


OLD_IMPORT = """
from data.storage.positions_repository import (
    PositionsRepository
)
"""

NEW_IMPORT = """
from data.storage.repositories.trades_repository import (
    TradesRepository
)
"""


FILES_TO_UPDATE = [
    ROOT / "core/agents/execution_agent.py",
    ROOT / "core/agents/risk_agent.py",
    ROOT / "core/agents/position_manager_agent.py",
]


REPLACEMENTS = {
    "PositionsRepository()": "TradesRepository()",

    "create_position(": "create_trade(",

    "get_open_position(": "get_open_trade(",

    "get_open_positions(": "get_open_trades(",

    "has_open_position(": "has_open_trade(",

    "update_price(": "update_trade_price(",

    "close_position(": "close_trade(",
}


TRADES_REPOSITORY_CONTENT = '''# -*- coding: utf-8 -*-

from datetime import datetime

from sqlalchemy.orm import Session

from data.storage.database import SessionLocal

from data.storage.models import Trade


class TradesRepository:

    def _session(self) -> Session:

        return SessionLocal()

    def create_trade(
        self,
        user_id: int,
        symbol: str,
        action: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        trailing_stop: float,
        breakeven_enabled: bool = True
    ):

        session = self._session()

        try:

            trade = Trade(
                user_id=user_id,
                symbol=symbol,
                action=action,
                entry_price=entry_price,
                current_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                trailing_stop=trailing_stop,
                breakeven_enabled=breakeven_enabled,
                status="OPEN",
                pnl=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                highest_price=entry_price,
                lowest_price=entry_price
            )

            session.add(trade)

            session.commit()

            session.refresh(trade)

            return trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    def get_open_trade(
        self,
        user_id: int,
        symbol: str
    ):

        session = self._session()

        try:

            return (
                session.query(Trade)
                .filter(
                    Trade.user_id == user_id,
                    Trade.symbol == symbol,
                    Trade.status == "OPEN"
                )
                .first()
            )

        finally:

            session.close()

    def get_open_trades(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            return (
                session.query(Trade)
                .filter(
                    Trade.user_id == user_id,
                    Trade.status == "OPEN"
                )
                .all()
            )

        finally:

            session.close()

    def has_open_trade(
        self,
        user_id: int,
        symbol: str
    ) -> bool:

        trade = self.get_open_trade(
            user_id=user_id,
            symbol=symbol
        )

        return trade is not None

    def update_trade_price(
        self,
        trade_id: int,
        current_price: float,
        unrealized_pnl: float
    ):

        session = self._session()

        try:

            trade = (
                session.query(Trade)
                .filter(
                    Trade.id == trade_id
                )
                .first()
            )

            if not trade:
                return None

            trade.current_price = current_price

            trade.unrealized_pnl = unrealized_pnl

            if current_price > (
                trade.highest_price or current_price
            ):
                trade.highest_price = current_price

            if current_price < (
                trade.lowest_price or current_price
            ):
                trade.lowest_price = current_price

            session.commit()

            session.refresh(trade)

            return trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        pnl: float,
        reason: str
    ):

        session = self._session()

        try:

            trade = (
                session.query(Trade)
                .filter(
                    Trade.id == trade_id
                )
                .first()
            )

            if not trade:
                return None

            trade.current_price = exit_price

            trade.pnl = pnl

            trade.realized_pnl = pnl

            trade.unrealized_pnl = 0.0

            trade.status = "CLOSED"

            trade.exit_reason = reason

            trade.closed_at = datetime.utcnow()

            session.commit()

            session.refresh(trade)

            return trade

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()
'''


INIT_CONTENT = '''# -*- coding: utf-8 -*-
'''


def ensure_repository_structure():

    repo_dir = ROOT / "data/storage/repositories"

    repo_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    init_file = repo_dir / "__init__.py"

    init_file.write_text(
        INIT_CONTENT,
        encoding="utf-8"
    )

    trades_file = repo_dir / "trades_repository.py"

    trades_file.write_text(
        TRADES_REPOSITORY_CONTENT,
        encoding="utf-8"
    )

    print("[OK] repositories created")


def update_agents():

    for file_path in FILES_TO_UPDATE:

        if not file_path.exists():

            print(f"[SKIP] {file_path}")
            continue

        content = file_path.read_text(
            encoding="utf-8"
        )

        content = content.replace(
            OLD_IMPORT,
            NEW_IMPORT
        )

        for old, new in REPLACEMENTS.items():

            content = content.replace(
                old,
                new
            )

        file_path.write_text(
            content,
            encoding="utf-8"
        )

        print(f"[OK] updated {file_path.name}")


def remove_legacy_repository():

    legacy = ROOT / "data/storage/positions_repository.py"

    if legacy.exists():

        legacy.unlink()

        print("[OK] removed positions_repository.py")


def main():

    print()
    print("===================================")
    print("Repository Layer Refactor")
    print("===================================")
    print()

    ensure_repository_structure()

    update_agents()

    remove_legacy_repository()

    print()
    print("[DONE] Repository Layer Refactor Complete")
    print()


if __name__ == "__main__":

    main()