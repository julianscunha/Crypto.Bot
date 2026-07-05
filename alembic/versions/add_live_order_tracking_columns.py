"""add_live_order_tracking_columns"""

from alembic import op

import sqlalchemy as sa


revision = "add_live_order_tracking_columns"

down_revision = "add_take_profit_extended_column"

branch_labels = None

depends_on = None


def upgrade():

    # =====================================================
    # LIVE ORDER TRACKING
    # =====================================================
    #
    # Tracks the real Binance order identifiers for a live trade --
    # entry_order_id (the market BUY in
    # core/services/execution_router.py's place_market_order call)
    # and order_list_id (the protective OCO from
    # place_oco_sell_order). Both responses already existed at the
    # call site but were discarded immediately after a successful
    # placement, since nothing downstream needed them yet.
    #
    # core/agents/position_manager_agent.py currently decides
    # STOP_LOSS/TAKE_PROFIT/TRAILING_STOP exits by comparing the
    # local market price feed against the locally stored
    # stop_loss/take_profit columns, then marks the trade closed in
    # the database -- without ever placing a real order or touching
    # the exchange. That is correct for PAPER (there is no real
    # position to protect), but for LIVE it means: (1) a TRAILING_STOP
    # exit, which has no corresponding resting order on Binance at
    # all, never actually closes the real position -- it stays open
    # and unprotected on the exchange while the local database shows
    # it as closed; (2) even a STOP_LOSS/TAKE_PROFIT exit, which the
    # OCO *should* cover, is marked closed locally without ever
    # confirming the OCO actually filled on the exchange's side.
    #
    # Both columns are nullable: PAPER trades never place a real
    # order and will always leave these NULL, which is also how
    # downstream LIVE-only logic distinguishes "this trade has no
    # real order to reconcile/cancel" from "the order id genuinely
    # wasn't captured" -- the latter should never happen for a LIVE
    # trade once execution_router.py is updated to populate them.

    op.add_column(
        "trades",
        sa.Column(
            "entry_order_id",
            sa.String(64),
            nullable=True
        )
    )

    op.add_column(
        "trades",
        sa.Column(
            "order_list_id",
            sa.String(64),
            nullable=True
        )
    )


def downgrade():

    op.drop_column(
        "trades",
        "order_list_id"
    )

    op.drop_column(
        "trades",
        "entry_order_id"
    )
