"""Merge training session migrations

Revision ID: 8a3c0c42e524
Revises: 7465e63e0491, 92fe46bfd4df
Create Date: 2025-09-12 11:05:24.568181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a3c0c42e524'
down_revision: Union[str, None] = ('7465e63e0491', '92fe46bfd4df')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
