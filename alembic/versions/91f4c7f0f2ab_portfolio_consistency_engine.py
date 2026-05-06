"""portfolio_consistency_engine"""

from alembic import op

import sqlalchemy as sa


revision = "91f4c7f0f2ab"

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
