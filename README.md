# AI Agents API

基于 FastAPI 的 AI 代理系统，包含 JWT 认证功能。

## 🚀 快速开始

### 1. 环境设置

```bash
# 克隆项目
git clone <your-repo-url>
cd ai-agents

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的配置
# 至少需要配置：
# - SECRET_KEY: JWT 密钥
# - DATABASE_URL: 数据库连接字符串
```

### 3. 数据库设置

确保 MySQL 数据库已启动，并创建对应的数据库：

```sql
-- 开发环境
CREATE DATABASE ai_agents_dev;

-- 生产环境
CREATE DATABASE ai_agents;
```

### 4. 运行应用

```bash
# 开发模式
python run.py

# 或者直接使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 查看应用。

## 📁 项目结构

```
ai-agents/
├── app/
│   ├── api/v1/          # API 路由
│   ├── core/            # 核心配置和数据库
│   ├── schemas/         # Pydantic 模型
│   ├── services/        # 业务逻辑
│   └── utils/           # 工具函数
├── static/              # 静态文件
├── .env.example         # 环境变量模板
├── requirements.txt     # Python 依赖
└── README.md           # 项目说明
```

## ⚙️ 环境配置

项目支持多环境配置，主要环境变量：

- `SECRET_KEY`: JWT 密钥（必须）
- `DATABASE_URL`: 数据库连接字符串（必须）
- `ENVIRONMENT`: 环境类型 (development/production)
- `DEBUG`: 调试模式 (true/false)
- `LOG_LEVEL`: 日志级别 (DEBUG/INFO/WARNING/ERROR)

## 🔧 开发

### API 文档

启动应用后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 添加新功能

1. 在 `app/api/v1/endpoints/` 添加新的端点
2. 在 `app/schemas/` 添加 Pydantic 模型
3. 在 `app/services/` 添加业务逻辑
4. 更新路由注册

## 📦 部署

生产环境部署时：

1. 设置环境变量 `ENVIRONMENT=production`
2. 使用强密钥作为 `SECRET_KEY`
3. 配置生产数据库
4. 设置 `DEBUG=false`
5. 配置适当的 `CORS_ORIGINS`

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

