"""Remove TrainingSession table and session_id from training messages

Revision ID: 92fe46bfd4df
Revises: 27334820374b
Create Date: 2025-01-12 10:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '92fe46bfd4df'
down_revision: Union[str, None] = '27334820374b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop foreign key constraint and session_id column from digital_human_training_messages
    with op.batch_alter_table('digital_human_training_messages', schema=None) as batch_op:
        batch_op.drop_constraint('digital_human_training_messages_ibfk_3', type_='foreignkey')
        batch_op.drop_column('session_id')
    
    # Drop the training_sessions table
    op.drop_table('training_sessions')


def downgrade() -> None:
    # Recreate the training_sessions table
    op.create_table('training_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('digital_human_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(100), nullable=False),
        sa.Column('session_type', sa.String(50), nullable=True),
        sa.Column('status', sa.Enum('in_progress', 'completed', 'applied', 'cancelled', name='training_status'), nullable=True),
        sa.Column('total_messages', sa.Integer(), nullable=True),
        sa.Column('extracted_entities', sa.Integer(), nullable=True),
        sa.Column('extracted_relations', sa.Integer(), nullable=True),
        sa.Column('knowledge_summary', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['digital_human_id'], ['digital_humans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_training_sessions_digital_human_id'), 'training_sessions', ['digital_human_id'], unique=False)
    op.create_index(op.f('ix_training_sessions_id'), 'training_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_training_sessions_thread_id'), 'training_sessions', ['thread_id'], unique=True)
    op.create_index(op.f('ix_training_sessions_user_id'), 'training_sessions', ['user_id'], unique=False)
    
    # Add session_id column back to digital_human_training_messages
    with op.batch_alter_table('digital_human_training_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_digital_human_training_messages_session_id', ['session_id'], unique=False)
        batch_op.create_foreign_key('digital_human_training_messages_ibfk_3', 'training_sessions', ['session_id'], ['id'])