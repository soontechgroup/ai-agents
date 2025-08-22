# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI Agents 是一个基于 FastAPI 的后端系统，提供 AI 代理服务，集成了多种数据库（MySQL、MongoDB、Neo4j、ChromaDB）并支持 LangChain/LangGraph 来构建对话式 AI 代理。

## 开发命令

### 启动应用

```bash
# 先启动所有数据库
docker-compose up -d

# 运行应用（默认开发环境）
python run.py

# 指定参数运行
python run.py --env dev --host 0.0.0.0 --port 8000 --reload

# 使用 shell 脚本
./scripts/run.sh start
./scripts/run.sh dev  # 开发模式
```

### 数据库管理

```bash
# 启动所有数据库
docker-compose up -d

# 启动特定数据库
docker-compose up -d mysql
docker-compose up -d mongodb  
docker-compose up -d neo4j

# 查看数据库状态
docker-compose ps

# 停止数据库
docker-compose down
```

### 数据库连接信息
- **MySQL**: `localhost:3306` (root/123456)
- **MongoDB**: `localhost:27018` (admin/password123)
- **Neo4j**: `localhost:7474` (浏览器), `localhost:7687` (Bolt协议) (neo4j/password123)

### 安装依赖

```bash
pip install -r requirements.txt
```

## 系统架构

### 分层架构模式

应用采用严格的分层架构：

```
API 层 (FastAPI 路由)
    ↓
服务层 (业务逻辑)
    ↓
仓储层 (数据访问)
    ↓
数据库层 (多数据库)
```

### 核心组件

1. **API 层** (`app/api/v1/endpoints/`)
   - FastAPI 路由处理 HTTP 请求
   - 通过 Pydantic schemas 进行输入验证
   - JWT 认证保护端点

2. **服务层** （计划中但未完全实现）
   - 业务逻辑和编排
   - AI 模型集成（LangChain/LangGraph）

3. **仓储层** (`app/repositories/`)
   - 数据访问抽象
   - `graph/` - Neo4j 图数据库操作
   - `conversation_repository.py` - 对话数据管理

4. **依赖注入** (`app/dependencies/`)
   - 服务的依赖注入
   - 数据库会话管理
   - 图数据库连接

### 数据库策略

系统使用多个数据库来满足不同需求：

- **MySQL**: 用户认证、系统元数据
- **MongoDB**: 文档存储、对话历史
- **Neo4j**: 知识图谱、关系映射
- **ChromaDB**: 向量存储、语义搜索

### 核心模块

#### 认证系统
- 基于 JWT 的认证
- 用户注册和登录
- 依赖注入保护端点
- 位置：`app/api/v1/endpoints/auth.py`、`app/api/v1/endpoints/user.py`

#### 对话管理
- 基于 LangGraph 的对话流
- 多后端内存管理
- 通过 SSE 的流式响应
- 位置：`app/api/v1/endpoints/conversations.py`

#### 向量数据库（ChromaDB）
- 集合管理
- 文档嵌入和检索
- 语义搜索能力
- 位置：`app/api/v1/endpoints/chroma.py`

#### 图数据库（Neo4j）
- 知识图谱构建
- 实体和关系管理
- 基于图的查询
- 位置：`app/api/v1/endpoints/graph.py`

### 响应标准化

所有 API 响应遵循 `app/utils/response.py` 中定义的统一格式：

```python
{
    "code": 200,
    "message": "成功",
    "data": {...}
}
```

### 配置管理

- 通过 `.env.dev` 进行环境配置
- 配置集中在 `app/core/config.py`
- 仅支持开发环境（生产环境配置未实现）

### 日志系统

- 使用 Loguru 进行结构化日志记录
- 请求 ID 跟踪用于分布式追踪
- 位置：`app/core/logger.py`

## API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 静态文件

`static/` 目录包含独立的 `chroma-test.html` 文件，用于测试 ChromaDB 向量操作。

## 重要设计决策

1. **无测试框架**：项目目前没有测试设置，建议添加 pytest 进行测试。

2. **服务层不完整**：虽然架构建议使用服务层，但大部分业务逻辑目前在 API 端点中。

3. **数据库迁移**：使用 Alembic 进行 MySQL 迁移，但也支持通过 SQLAlchemy 自动迁移。

4. **异步操作**：所有数据库操作都应该是异步兼容的，以获得更好的性能。

5. **内存管理**：系统包含 AI 代理的混合内存系统，支持多种后端选项（在 `app/core/memory/` 中）。

## 当前实现状态

### 已完成 ✅
- 用户认证（JWT）
- 所有数据库的基本 CRUD 操作
- ChromaDB 集成用于向量搜索
- Neo4j 图操作
- LangGraph 对话流

### 待完成 ⚠️
- 完整的服务层实现
- 生产环境配置
- Redis 缓存层
- 消息队列集成
- 全面的错误处理
- 单元和集成测试

## 常见问题避免

1. 运行应用前不要忘记启动 Docker 容器
2. 确保 `.env.dev` 中的数据库 URL 与 docker-compose 端口匹配
3. 始终使用 `app/utils/response.py` 中的标准化响应格式
4. 维护分层架构 - 避免从 API 端点直接访问数据库