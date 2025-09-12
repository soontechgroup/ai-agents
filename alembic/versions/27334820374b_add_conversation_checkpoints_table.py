"""add conversation checkpoints table

Revision ID: 27334820374b
Revises: f221ff79268b
Create Date: 2025-01-10 18:32:19.570486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27334820374b'
down_revision: Union[str, None] = 'f221ff79268b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 conversation_checkpoints 表
    op.create_table('conversation_checkpoints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(length=100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, comment='检查点版本号'),
        sa.Column('parent_version', sa.Integer(), nullable=True, comment='父版本号，用于分支'),
        sa.Column('checkpoint_data', sa.JSON(), nullable=False, comment='完整的检查点数据'),
        sa.Column('channel_values', sa.JSON(), nullable=False, comment='通道值（消息等）'),
        sa.Column('channel_versions', sa.JSON(), nullable=True, comment='通道版本信息'),
        sa.Column('checkpoint_metadata', sa.JSON(), nullable=True, comment='检查点元数据'),
        sa.Column('task_id', sa.String(length=100), nullable=True, comment='任务ID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id', 'version', name='uq_thread_version')
    )
    
    # 创建索引
    op.create_index('idx_thread_version', 'conversation_checkpoints', ['thread_id', 'version'], unique=False)
    op.create_index(op.f('ix_conversation_checkpoints_conversation_id'), 'conversation_checkpoints', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_checkpoints_id'), 'conversation_checkpoints', ['id'], unique=False)
    op.create_index(op.f('ix_conversation_checkpoints_task_id'), 'conversation_checkpoints', ['task_id'], unique=False)
    op.create_index(op.f('ix_conversation_checkpoints_thread_id'), 'conversation_checkpoints', ['thread_id'], unique=False)


def downgrade() -> None:
    # 删除索引
    op.drop_index(op.f('ix_conversation_checkpoints_thread_id'), table_name='conversation_checkpoints')
    op.drop_index(op.f('ix_conversation_checkpoints_task_id'), table_name='conversation_checkpoints')
    op.drop_index(op.f('ix_conversation_checkpoints_id'), table_name='conversation_checkpoints')
    op.drop_index(op.f('ix_conversation_checkpoints_conversation_id'), table_name='conversation_checkpoints')
    op.drop_index('idx_thread_version', table_name='conversation_checkpoints')
    
    # 删除表
    op.drop_table('conversation_checkpoints')