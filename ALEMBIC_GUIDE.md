# Alembic 数据库迁移指南

## 概述
项目已成功接入 Alembic 数据库迁移工具，替代了之前的 `init.sql` 文件。

## 常用命令

### 1. 生成迁移文件
```bash
# 自动生成迁移（推荐）
alembic revision --autogenerate -m "描述你的修改"

# 手动创建空迁移文件
alembic revision -m "描述你的修改"
```

### 2. 应用迁移
```bash
# 升级到最新版本
alembic upgrade head

# 升级到指定版本
alembic upgrade <revision_id>
```

### 3. 回滚迁移
```bash
# 回滚到上一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision_id>
```

### 4. 查看迁移状态
```bash
# 查看当前版本
alembic current

# 查看迁移历史
alembic history

# 查看详细历史
alembic history --verbose
```

## 开发工作流程

### 修改数据库结构
1. 修改 `app/core/models.py` 中的 ORM 模型
2. 生成迁移文件：`alembic revision --autogenerate -m "描述修改"`
3. 检查生成的迁移文件（在 `alembic/versions/` 目录下）
4. 应用迁移：`alembic upgrade head`

### 示例：添加新字段
```python
# 1. 修改 models.py
class User(Base):
    # ... 现有字段
    phone = Column(String(20), nullable=True)  # 新增字段

# 2. 生成迁移
# alembic revision --autogenerate -m "Add phone field to users"

# 3. 应用迁移
# alembic upgrade head
```

## 部署流程

### 新环境部署
1. 创建数据库：`CREATE DATABASE ai_agents;`
2. 安装依赖：`pip install -r requirements.txt`
3. 应用迁移：`alembic upgrade head`
4. 启动应用：`python run.py`

### 更新现有环境
1. 拉取最新代码
2. 安装新依赖（如有）
3. 应用迁移：`alembic upgrade head`
4. 重启应用

## 注意事项

1. **不要手动修改数据库结构**，始终通过 Alembic 迁移
2. **提交代码前确保迁移文件正确**
3. **生产环境部署前先在测试环境验证迁移**
4. **备份数据库后再执行迁移**（生产环境）

## 配置文件

- `alembic.ini` - Alembic 主配置文件
- `alembic/env.py` - 环境配置，连接应用模型
- `alembic/versions/` - 迁移版本文件目录

## 故障排除

### 常见问题
1. **迁移冲突**：多人开发时可能出现版本冲突
2. **数据库连接失败**：检查 `alembic.ini` 中的数据库连接配置
3. **模型导入失败**：检查 `alembic/env.py` 中的模型导入路径

### 解决方案
```bash
# 查看当前状态
alembic current

# 强制标记为最新版本（谨慎使用）
alembic stamp head

# 查看 SQL 而不执行
alembic upgrade head --sql
``` 