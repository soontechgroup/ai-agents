"""add_digital_human_training_messages_table

Revision ID: f221ff79268b
Revises: 641c819ac495
Create Date: 2025-09-04 11:32:31.764636

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f221ff79268b'
down_revision: Union[str, None] = '641c819ac495'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create digital_human_training_messages table
    op.create_table('digital_human_training_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('digital_human_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('user', 'assistant', name='training_message_role'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('extracted_knowledge', sa.JSON(), nullable=True),
        sa.Column('extraction_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['digital_human_id'], ['digital_humans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_digital_human', 'digital_human_training_messages', ['digital_human_id'], unique=False)


def downgrade() -> None:
    # Drop indexes and table
    op.drop_index('idx_digital_human', table_name='digital_human_training_messages')
    op.drop_table('digital_human_training_messages')
    # Drop enum type
    sa.Enum('user', 'assistant', name='training_message_role').drop(op.get_bind())