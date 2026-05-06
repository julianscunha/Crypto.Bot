"""add_created_at_column"""

from alembic import op
import sqlalchemy as sa


revision = "add_created_at_column"
down_revision = "add_breakeven_column"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column(
        "trades",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=True
        )
    )


def downgrade():

    op.drop_column(
        "trades",
        "created_at"
    )