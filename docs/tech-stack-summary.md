# AI Agents 技术栈文档总览

## 📁 文档结构

### 01-基础设施 (Infrastructure)
- **Docker** - 容器化平台，管理数据库服务
- **Python 3.12+** - 项目运行环境

### 02-数据存储 (Data Storage)
- **MySQL** - 关系型数据库，存储用户、数字人等结构化数据
- **MongoDB** - 文档数据库，存储对话历史和非结构化数据
- **Neo4j** - 图数据库，构建知识图谱
- **ChromaDB** - 向量数据库，语义搜索和相似度匹配

### 03-数据访问 (Data Access)
- **SQLAlchemy** - MySQL ORM 框架
- **PyMySQL** - SQLAlchemy 的 MySQL 驱动
- **Beanie** - MongoDB ODM 框架
- **Neo4j Driver** - Neo4j 图数据库驱动

### 04-Web框架 (Web Framework)
- **FastAPI** - 高性能异步 Web 框架
- **Pydantic** - 数据验证和序列化

### 05-安全认证 (Security)
- **JWT** - JSON Web Token 认证
- **Passlib** - 密码哈希加密

### 06-AI/ML (AI & Machine Learning)
- **LangChain** - LLM 应用开发框架
- **LangGraph** - 有状态工作流编排
- **OpenAI GPT** - 大语言模型 API

### 07-通信协议 (Communication)
- **SSE** - 服务器推送事件，实现流式响应

### 08-开发工具 (Tools)
- **Alembic** - 数据库迁移管理
- **Loguru** - 日志记录系统

## 📋 文档优化原则

所有技术栈文档遵循统一的简化原则：

1. **删除理论介绍** - 只保留实际使用说明
2. **删除对比内容** - 不需要"使用前/使用后"对比
3. **聚焦项目应用** - 使用项目中的实际代码示例
4. **验证实际使用** - 只记录已实现的功能

## 📊 优化成果

| 文档 | 优化前行数 | 优化后行数 | 精简比例 |
|------|-----------|-----------|---------|
| PyMySQL | 1047 | 81 | 92.3% |
| Alembic | 1135 | 209 | 81.6% |
| Loguru | 1451 | 235 | 83.8% |
| Passlib | 779 | 105 | 86.5% |
| SSE | 原始 | 262 | - |

## 🎯 核心价值

- **实用性** - 每个文档都是可直接使用的参考手册
- **一致性** - 统一的文档结构和格式
- **准确性** - 与项目代码实现完全一致
- **简洁性** - 去除冗余，保留核心内容