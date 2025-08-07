"""add_missing_fields_to_digital_humans

Revision ID: 641c819ac495
Revises: f1461e96b103
Create Date: 2025-08-07 19:09:18.094310

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '641c819ac495'
down_revision: Union[str, None] = 'f1461e96b103'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加缺失的字段到 digital_humans 表
    op.add_column('digital_humans', 
        sa.Column('system_prompt', sa.Text(), nullable=True, comment='系统提示词'))
    op.add_column('digital_humans', 
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1', comment='模板是否启用（启用后可用于创建对话）'))
    op.add_column('digital_humans', 
        sa.Column('is_public', sa.Boolean(), nullable=True, server_default='0', comment='是否公开模板'))


def downgrade() -> None:
    # 回滚：删除添加的字段
    op.drop_column('digital_humans', 'is_public')
    op.drop_column('digital_humans', 'is_active')
    op.drop_column('digital_humans', 'system_prompt')
