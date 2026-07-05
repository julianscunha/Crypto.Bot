"""add_runtime_state_table"""

from alembic import op

import sqlalchemy as sa


revision = "add_runtime_state_table"

down_revision = "add_position_lifecycle_columns"

branch_labels = None

depends_on = None


def upgrade():

    # =====================================================
    # RUNTIME STATE
    # =====================================================
    #
    # Single-row table (always id=1, upserted) sharing live market/
    # runtime telemetry between the API and Runner OS processes
    # under Full Stack -- see
    # data/storage/repositories/runtime_state_repository.py and
    # core/state/market_state.py for the full explanation of why
    # this table exists at all (MarketState is an in-memory
    # singleton that doesn't cross process boundaries).

    op.create_table(
        "runtime_state",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True
        ),

        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=False
        ),

        sa.Column(
            "websocket_connected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false()
        ),

        sa.Column(
            "total_market_messages",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "last_market_message_at",
            sa.DateTime(),
            nullable=True
        ),

        sa.Column(
            "active_symbols_json",
            sa.String(500),
            nullable=False,
            server_default="[]"
        ),

        sa.Column(
            "total_analysis_requests",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "total_generated_signals",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "total_approved_signals",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "total_rejected_signals",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "total_executed_orders",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "total_closed_positions",
            sa.Integer(),
            nullable=False,
            server_default="0"
        ),

        sa.Column(
            "blocked_signal_reasons_json",
            sa.String(2000),
            nullable=False,
            server_default="{}"
        ),

        sa.Column(
            "execution_reasons_json",
            sa.String(2000),
            nullable=False,
            server_default="{}"
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False
        )
    )


def downgrade():

    op.drop_table(
        "runtime_state"
    )
