"""add_equity_curve

Revision ID: 30da39360606
Revises: position_lifecycle_engine
Create Date: 2026-05-06 11:59:09.785180

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30da39360606'
down_revision: Union[str, None] = 'position_lifecycle_engine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
