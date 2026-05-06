"""position_lifecycle_engine"""

from alembic import op
import sqlalchemy as sa


revision = "position_lifecycle_engine"
down_revision = "add_created_at_column"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column(
        "trades",
        sa.Column(
            "exit_reason",
            sa.String(),
            nullable=True
        )
    )


def downgrade():

    op.drop_column("trades", "exit_reason")