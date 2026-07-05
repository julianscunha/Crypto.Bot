"""add_position_lifecycle_columns"""

from alembic import op

import sqlalchemy as sa


revision = "add_position_lifecycle_columns"

down_revision = "91f4c7f0f2ab"

branch_labels = None

depends_on = None


def upgrade():

    # =====================================================
    # POSITION LIFECYCLE COLUMNS
    # =====================================================
    #
    # These columns exist in trades.db (created out-of-band by an
    # earlier version of the code / a manual schema sync) but were
    # never actually added by any tracked migration. Without this,
    # `alembic upgrade head` on a fresh database produces a `trades`
    # table missing columns that PositionLifecycleService, the ORM
    # model, and the API all depend on.

    op.add_column(
        "trades",
        sa.Column(
            "highest_price",
            sa.Float(),
            nullable=True
        )
    )

    op.add_column(
        "trades",
        sa.Column(
            "lowest_price",
            sa.Float(),
            nullable=True
        )
    )

    op.add_column(
        "trades",
        sa.Column(
            "unrealized_pnl",
            sa.Float(),
            nullable=False,
            server_default="0.0"
        )
    )

    op.add_column(
        "trades",
        sa.Column(
            "realized_pnl",
            sa.Float(),
            nullable=False,
            server_default="0.0"
        )
    )


def downgrade():

    op.drop_column("trades", "realized_pnl")

    op.drop_column("trades", "unrealized_pnl")

    op.drop_column("trades", "lowest_price")

    op.drop_column("trades", "highest_price")
