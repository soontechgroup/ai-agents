"""merge multiple heads

Revision ID: ead18872c32d
Revises: 8a3c0c42e524, 67230a25a710
Create Date: 2025-09-18 11:14:12.851057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ead18872c32d'
down_revision: Union[str, None] = ('8a3c0c42e524', '67230a25a710')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
