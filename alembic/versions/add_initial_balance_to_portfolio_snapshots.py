"""add_initial_balance_to_portfolio_snapshots"""

from alembic import op

import sqlalchemy as sa


revision = "add_initial_balance_to_portfolio_snapshots"

down_revision = "add_runtime_state_table"

branch_labels = None

depends_on = None


def upgrade():

    # =====================================================
    # INITIAL BALANCE (SESSION SCOPING)
    # =====================================================
    #
    # Without this column, PortfolioRepository.get_max_equity()
    # could only compute a historical equity peak across ALL
    # snapshots for a user_id, regardless of what account_balance
    # the bot was configured with at the time. Deliberately
    # resetting the paper account (e.g. lowering account_balance
    # from 100 to 10 in core/config/trading_config.py) left old,
    # much higher equity snapshots in the table, which then got
    # misread as a real ~90% trading loss against the new $10
    # baseline -- see core/services/portfolio_service.py and
    # data/storage/repositories/portfolio_repository.py for the
    # full fix.
    #
    # Existing rows get initial_balance=0.0 (the server_default),
    # which simply means they're never selected by an
    # initial_balance-scoped get_max_equity() lookup -- not zeroed
    # out or treated as an error.

    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "initial_balance",
            sa.Float(),
            nullable=False,
            server_default="0.0"
        )
    )


def downgrade():

    op.drop_column(
        "portfolio_snapshots",
        "initial_balance"
    )
