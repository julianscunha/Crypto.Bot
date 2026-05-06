"""add_breakeven_column"""

from alembic import op
import sqlalchemy as sa


revision = "add_breakeven_column"
down_revision = "initial_schema"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column(
        "trades",
        sa.Column(
            "breakeven_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="0"
        )
    )


def downgrade():

    op.drop_column(
        "trades",
        "breakeven_enabled"
    )