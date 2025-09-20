"""remove conversation concept use thread_id directly

Revision ID: 67230a25a710
Revises: 11ccaae4fb03
Create Date: 2025-09-18 09:37:31.322551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '67230a25a710'
down_revision: Union[str, None] = '11ccaae4fb03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 向 messages 表添加新字段
    op.add_column('messages', sa.Column('thread_id', sa.String(100), nullable=True))
    op.add_column('messages', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('messages', sa.Column('digital_human_id', sa.Integer(), nullable=True))

    # 2. 从 conversations 表迁移数据到 messages 表
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        UPDATE messages m
        JOIN conversations c ON m.conversation_id = c.id
        SET m.thread_id = c.thread_id,
            m.user_id = c.user_id,
            m.digital_human_id = c.digital_human_id
    """))

    # 3. 向 conversation_checkpoints 表添加新字段
    op.add_column('conversation_checkpoints', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('conversation_checkpoints', sa.Column('digital_human_id', sa.Integer(), nullable=True))

    # 4. 从 conversations 表迁移数据到 conversation_checkpoints 表
    result = connection.execute(sa.text("""
        UPDATE conversation_checkpoints cp
        JOIN conversations c ON cp.conversation_id = c.id
        SET cp.user_id = c.user_id,
            cp.digital_human_id = c.digital_human_id
    """))

    # 5. 设置新字段为非空（在数据迁移后）
    op.alter_column('messages', 'thread_id',
               existing_type=sa.String(100),
               nullable=False)
    op.alter_column('messages', 'user_id',
               existing_type=sa.Integer(),
               nullable=False)

    # 6. 创建索引
    op.create_index('ix_messages_thread_id', 'messages', ['thread_id'])
    op.create_index('ix_messages_user_id', 'messages', ['user_id'])

    # 7. 添加外键约束
    op.create_foreign_key('fk_messages_user_id', 'messages', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_messages_digital_human_id', 'messages', 'digital_humans', ['digital_human_id'], ['id'])
    op.create_foreign_key('fk_checkpoints_user_id', 'conversation_checkpoints', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_checkpoints_digital_human_id', 'conversation_checkpoints', 'digital_humans', ['digital_human_id'], ['id'])

    # 8. 删除旧的外键和字段
    op.drop_constraint('messages_ibfk_1', 'messages', type_='foreignkey')
    op.drop_column('messages', 'conversation_id')

    # 9. 删除 conversation_checkpoints 表的 conversation_id
    op.drop_constraint('conversation_checkpoints_ibfk_1', 'conversation_checkpoints', type_='foreignkey')
    op.drop_index('ix_conversation_checkpoints_conversation_id', 'conversation_checkpoints')
    op.drop_column('conversation_checkpoints', 'conversation_id')

    # 10. 删除 conversations 表
    op.drop_table('conversations')


def downgrade() -> None:
    # 1. 重新创建 conversations 表
    op.create_table('conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('digital_human_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('thread_id', sa.String(100), nullable=False),
        sa.Column('status', sa.Enum('active', 'archived', 'deleted', name='conversation_status'), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['digital_human_id'], ['digital_humans.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id')
    )

    # 2. 向 messages 表添加 conversation_id
    op.add_column('messages', sa.Column('conversation_id', sa.Integer(), nullable=True))

    # 3. 向 conversation_checkpoints 表添加 conversation_id
    op.add_column('conversation_checkpoints', sa.Column('conversation_id', sa.Integer(), nullable=True))
    op.create_index('ix_conversation_checkpoints_conversation_id', 'conversation_checkpoints', ['conversation_id'])

    # 4. 从 messages 和 checkpoints 恢复数据到 conversations
    # 这部分较复杂，实际生产中可能需要特别处理

    # 5. 删除新添加的字段和约束
    op.drop_constraint('fk_messages_user_id', 'messages', type_='foreignkey')
    op.drop_constraint('fk_messages_digital_human_id', 'messages', type_='foreignkey')
    op.drop_constraint('fk_checkpoints_user_id', 'conversation_checkpoints', type_='foreignkey')
    op.drop_constraint('fk_checkpoints_digital_human_id', 'conversation_checkpoints', type_='foreignkey')

    op.drop_index('ix_messages_thread_id', 'messages')
    op.drop_index('ix_messages_user_id', 'messages')

    op.drop_column('messages', 'thread_id')
    op.drop_column('messages', 'user_id')
    op.drop_column('messages', 'digital_human_id')

    op.drop_column('conversation_checkpoints', 'user_id')
    op.drop_column('conversation_checkpoints', 'digital_human_id')

    # 6. 重新创建外键
    op.create_foreign_key('messages_ibfk_1', 'messages', 'conversations', ['conversation_id'], ['id'])
    op.create_foreign_key('conversation_checkpoints_ibfk_1', 'conversation_checkpoints', 'conversations', ['conversation_id'], ['id'])