# Alembic 数据库迁移工具

## 📚 使用说明

项目使用 Alembic 进行数据库模式版本控制，自动管理数据库结构变更。

## 🛠 框架配置

### 安装依赖
```bash
pip install alembic
```

### 初始化配置
```bash
# 初始化Alembic
alembic init alembic

# 配置数据库连接
# alembic.ini
sqlalchemy.url = mysql+pymysql://root:123456@localhost:3306/ai_agents
```

### 环境配置
```python
# alembic/env.py
import os
import sys
from pathlib import Path

ROOT_PATH = Path(__file__).parent.parent
sys.path.append(str(ROOT_PATH))

from app.core.config import settings
from app.core.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata
```

## 💻 项目应用

### 核心表迁移
```python
# 生成初始迁移
$ alembic revision --autogenerate -m "create core tables"

# alembic/versions/001_create_core_tables.py
"""create core tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '001'
down_revision = None

def upgrade():
    # 创建用户表
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=200), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # 创建数字人表
    op.create_table('digital_humans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('skills', mysql.JSON(), nullable=True),
        sa.Column('personality', mysql.JSON(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('digital_humans')
    op.drop_table('users')
```

### 训练消息表迁移
```python
# 添加训练消息表
$ alembic revision --autogenerate -m "add training messages table"

# alembic/versions/002_add_training_messages.py
"""add training messages table

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '002'
down_revision = '001'

def upgrade():
    op.create_table('digital_human_training_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('digital_human_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('extracted_knowledge', mysql.JSON(), nullable=True),
        sa.Column('memory', mysql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['digital_human_id'], ['digital_humans.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 添加索引
    op.create_index('idx_training_messages_digital_human', 'digital_human_training_messages', ['digital_human_id'])
    op.create_index('idx_training_messages_user', 'digital_human_training_messages', ['user_id'])
    op.create_index('idx_training_messages_created', 'digital_human_training_messages', ['created_at'])

def downgrade():
    op.drop_index('idx_training_messages_created', table_name='digital_human_training_messages')
    op.drop_index('idx_training_messages_user', table_name='digital_human_training_messages')
    op.drop_index('idx_training_messages_digital_human', table_name='digital_human_training_messages')
    op.drop_table('digital_human_training_messages')
```

### 常用操作命令
```bash
# 生成迁移脚本
alembic revision --autogenerate -m "description"

# 应用迁移
alembic upgrade head

# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 回滚到上一版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision>
```

### 部署脚本
```bash
#!/bin/bash
# scripts/deploy_db.sh

echo "运行数据库迁移..."

# 检查当前版本
echo "当前数据库版本："
alembic current

# 应用迁移
alembic upgrade head

# 验证结果
echo "迁移后数据库版本："
alembic current

echo "数据库迁移完成！"
```

### 开发工作流
```bash
# 1. 修改模型后生成迁移
alembic revision --autogenerate -m "add new field"

# 2. 检查生成的迁移脚本
cat alembic/versions/xxx_add_new_field.py

# 3. 应用迁移
alembic upgrade head

# 4. 测试回滚
alembic downgrade -1
alembic upgrade head

# 5. 提交代码
git add alembic/versions/xxx_add_new_field.py
git commit -m "feat: add new field"
```

Alembic 为项目提供了专业的数据库版本控制能力，确保数据库变更的安全性和可追溯性。