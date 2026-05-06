from alembic import op
import sqlalchemy as sa

revision = "initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "trades",

        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),

        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),

        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=False),

        sa.Column("quantity", sa.Float(), nullable=False),

        sa.Column("stop_loss", sa.Float()),
        sa.Column("take_profit", sa.Float()),
        sa.Column("trailing_stop", sa.Float()),

        sa.Column("status", sa.String(), default="OPEN"),

        sa.Column("pnl", sa.Float(), default=0),

        sa.Column("opened_at", sa.DateTime()),
        sa.Column("closed_at", sa.DateTime())
    )

    op.create_table(
        "equity_curve",

        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),

        sa.Column("equity", sa.Float(), nullable=False),

        sa.Column("realized_pnl", sa.Float(), default=0),
        sa.Column("unrealized_pnl", sa.Float(), default=0),

        sa.Column("drawdown", sa.Float(), default=0),

        sa.Column("created_at", sa.DateTime())
    )


def downgrade():

    op.drop_table("trades")
    op.drop_table("equity_curve")