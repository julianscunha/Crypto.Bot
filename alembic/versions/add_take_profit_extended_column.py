"""add_take_profit_extended_column"""

from alembic import op

import sqlalchemy as sa


revision = "add_take_profit_extended_column"

down_revision = "add_initial_balance_to_portfolio_snapshots"

branch_labels = None

depends_on = None


def upgrade():

    # =====================================================
    # TAKE PROFIT EXTENDED
    # =====================================================
    #
    # Tracks whether the dynamic take-profit extension (see
    # core/agents/position_manager_agent.py's _apply_dynamic_take_profit)
    # has already been applied to this trade -- the extension only
    # ever fires once per trade, mirroring breakeven_enabled's
    # "already applied" semantics (see
    # add_take_profit_extended_column's sibling migration history
    # for breakeven_enabled, added earlier in this project).

    op.add_column(
        "trades",
        sa.Column(
            "take_profit_extended",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        )
    )


def downgrade():

    op.drop_column(
        "trades",
        "take_profit_extended"
    )
