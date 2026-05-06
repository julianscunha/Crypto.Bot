# -*- coding: utf-8 -*-

# =========================================================
# PORTFOLIO CONSISTENCY ENGINE
# =========================================================
#
# Objetivo:
# - Criar PortfolioSnapshot
# - Criar PortfolioRepository
# - Criar PortfolioService
# - Atualizar README_FULL.md
# - Gerar migration
#
# Execução:
# python .\scripts\portfolio_consistency_engine.py
#
# =========================================================

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


# =========================================================
# HELPERS
# =========================================================

def write_file(path: Path, content: str):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        content.strip() + "\n",
        encoding="utf-8"
    )

    print(f"[OK] {path}")


# =========================================================
# PORTFOLIO REPOSITORY
# =========================================================

PORTFOLIO_REPOSITORY = r'''
# -*- coding: utf-8 -*-

from sqlalchemy.orm import Session

from data.storage.database import SessionLocal

from data.storage.models import PortfolioSnapshot


class PortfolioRepository:

    def _session(self) -> Session:

        return SessionLocal()

    def create_snapshot(
        self,
        user_id: int,
        balance: float,
        equity: float,
        realized_pnl: float,
        unrealized_pnl: float,
        total_pnl: float,
        open_positions: int,
        closed_positions: int,
        exposure: float,
        drawdown: float
    ):

        session = self._session()

        try:

            snapshot = PortfolioSnapshot(
                user_id=user_id,
                balance=balance,
                equity=equity,
                realized_pnl=realized_pnl,
                unrealized_pnl=unrealized_pnl,
                total_pnl=total_pnl,
                open_positions=open_positions,
                closed_positions=closed_positions,
                exposure=exposure,
                drawdown=drawdown
            )

            session.add(snapshot)

            session.commit()

            session.refresh(snapshot)

            return snapshot

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()

    def get_latest_snapshot(
        self,
        user_id: int
    ):

        session = self._session()

        try:

            return (
                session.query(PortfolioSnapshot)
                .filter(
                    PortfolioSnapshot.user_id == user_id
                )
                .order_by(
                    PortfolioSnapshot.id.desc()
                )
                .first()
            )

        finally:

            session.close()
'''


# =========================================================
# PORTFOLIO SERVICE
# =========================================================

PORTFOLIO_SERVICE = r'''
# -*- coding: utf-8 -*-

from data.storage.repositories.trades_repository import (
    TradesRepository
)

from data.storage.repositories.portfolio_repository import (
    PortfolioRepository
)


class PortfolioService:

    def __init__(self):

        self.trades = TradesRepository()

        self.portfolio = PortfolioRepository()

    def build_snapshot(
        self,
        user_id: int,
        initial_balance: float = 1000.0
    ):

        open_trades = (
            self.trades.get_open_trades(
                user_id=user_id
            )
        )

        closed_trades = (
            self.trades.get_closed_trades(
                user_id=user_id
            )
        )

        realized_pnl = sum(
            trade.realized_pnl or 0.0
            for trade in closed_trades
        )

        unrealized_pnl = sum(
            trade.unrealized_pnl or 0.0
            for trade in open_trades
        )

        total_pnl = (
            realized_pnl +
            unrealized_pnl
        )

        balance = (
            initial_balance +
            realized_pnl
        )

        equity = (
            balance +
            unrealized_pnl
        )

        exposure = sum(
            (
                trade.current_price or 0.0
            ) * (
                trade.quantity or 0.0
            )
            for trade in open_trades
        )

        peak_equity = max(
            equity,
            initial_balance
        )

        drawdown = round(
            (
                (
                    peak_equity -
                    equity
                ) / peak_equity
            ) * 100,
            2
        )

        snapshot = (
            self.portfolio.create_snapshot(
                user_id=user_id,
                balance=round(balance, 2),
                equity=round(equity, 2),
                realized_pnl=round(realized_pnl, 2),
                unrealized_pnl=round(unrealized_pnl, 2),
                total_pnl=round(total_pnl, 2),
                open_positions=len(open_trades),
                closed_positions=len(closed_trades),
                exposure=round(exposure, 2),
                drawdown=drawdown
            )
        )

        print(
            f"[PORTFOLIO] "
            f"Equity={snapshot.equity} "
            f"| Exposure={snapshot.exposure} "
            f"| RealizedPnL={snapshot.realized_pnl} "
            f"| UnrealizedPnL={snapshot.unrealized_pnl} "
            f"| Drawdown={snapshot.drawdown}%"
        )

        return snapshot
'''


# =========================================================
# MODELS BLOCK
# =========================================================

MODELS_BLOCK = r'''

class PortfolioSnapshot(Base):

    __tablename__ = "portfolio_snapshots"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    balance = Column(
        Float,
        default=0.0
    )

    equity = Column(
        Float,
        default=0.0
    )

    realized_pnl = Column(
        Float,
        default=0.0
    )

    unrealized_pnl = Column(
        Float,
        default=0.0
    )

    total_pnl = Column(
        Float,
        default=0.0
    )

    open_positions = Column(
        Integer,
        default=0
    )

    closed_positions = Column(
        Integer,
        default=0
    )

    exposure = Column(
        Float,
        default=0.0
    )

    drawdown = Column(
        Float,
        default=0.0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
'''


# =========================================================
# MIGRATION
# =========================================================

MIGRATION = r'''
"""portfolio_consistency_engine"""

from alembic import op

import sqlalchemy as sa


revision = "portfolio_consistency_engine"

down_revision = "30da39360606"

branch_labels = None

depends_on = None


def upgrade():

    op.create_table(
        "portfolio_snapshots",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "balance",
            sa.Float(),
            default=0.0
        ),

        sa.Column(
            "equity",
            sa.Float(),
            default=0.0
        ),

        sa.Column(
            "realized_pnl",
            sa.Float(),
            default=0.0
        ),

        sa.Column(
            "unrealized_pnl",
            sa.Float(),
            default=0.0
        ),

        sa.Column(
            "total_pnl",
            sa.Float(),
            default=0.0
        ),

        sa.Column(
            "open_positions",
            sa.Integer(),
            default=0
        ),

        sa.Column(
            "closed_positions",
            sa.Integer(),
            default=0
        ),

        sa.Column(
            "exposure",
            sa.Float(),
            default=0.0
        ),

        sa.Column(
            "drawdown",
            sa.Float(),
            default=0.0
        ),

        sa.Column(
            "created_at",
            sa.DateTime()
        )
    )


def downgrade():

    op.drop_table(
        "portfolio_snapshots"
    )
'''


# =========================================================
# README BLOCK
# =========================================================

README_APPEND = r'''

# =========================================================
# PORTFOLIO CONSISTENCY ENGINE
# =========================================================

## COMPONENTS

- PortfolioSnapshot
- PortfolioRepository
- PortfolioService
- Equity Tracking
- Exposure Tracking
- Drawdown Engine
- Unrealized PnL Tracking

## FLOW

OPEN TRADE
    -> snapshot update

PRICE UPDATE
    -> unrealized pnl update

CLOSE TRADE
    -> realized pnl update

## METRICS

- equity
- exposure
- drawdown
- realized pnl
- unrealized pnl
- total pnl
- open positions
- closed positions
'''


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("========================================")
    print("PORTFOLIO CONSISTENCY ENGINE")
    print("========================================")
    print()

    # repository

    write_file(
        ROOT / "data/storage/repositories/portfolio_repository.py",
        PORTFOLIO_REPOSITORY
    )

    # service

    write_file(
        ROOT / "core/services/portfolio_service.py",
        PORTFOLIO_SERVICE
    )

    # migration

    write_file(
        ROOT / "alembic/versions/portfolio_consistency_engine.py",
        MIGRATION
    )

    # update models

    models_path = ROOT / "data/storage/models.py"

    models_content = models_path.read_text(
        encoding="utf-8"
    )

    if "class PortfolioSnapshot" not in models_content:

        models_content += MODELS_BLOCK

        models_path.write_text(
            models_content,
            encoding="utf-8"
        )

        print("[OK] models.py updated")

    # update README

    readme_path = ROOT / "README_FULL.md"

    if readme_path.exists():

        readme_content = readme_path.read_text(
            encoding="utf-8"
        )

        if "PORTFOLIO CONSISTENCY ENGINE" not in readme_content:

            readme_content += README_APPEND

            readme_path.write_text(
                readme_content,
                encoding="utf-8"
            )

            print("[OK] README_FULL.md updated")

    print()
    print("[DONE] Portfolio Consistency Engine generated")
    print()

    print("NEXT:")
    print("1. alembic upgrade head")
    print("2. .\\scripts\\start.ps1")
    print()


if __name__ == "__main__":

    main()