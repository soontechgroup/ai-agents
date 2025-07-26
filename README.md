# 环境配置说明

## 概述

本项目支持多环境配置，可以通过环境变量或命令行参数指定不同的运行环境。

## 支持的环境

- `dev` / `development` - 开发环境 (默认)

## 配置文件

- `.env.dev` - 开发环境配置
- `.env` - 默认配置文件（备用）

## 使用方法

### 1. 使用 Python 启动脚本

```bash
# 默认开发环境
python run.py

# 显式指定开发环境
python run.py --env dev

# 指定其他参数
python run.py --env dev --host 0.0.0.0 --port 9000
```

### 2. 使用 Shell 脚本

```bash
# 默认开发环境
./scripts/run.sh start

# 显式指定开发环境
ENVIRONMENT=dev ./scripts/run.sh start

# 开发模式
./scripts/run.sh dev
```

### 3. 直接设置环境变量

```bash
# 设置环境变量
export ENVIRONMENT=dev

# 启动应用
python run.py
# 或
./scripts/run.sh start
```

## Docker 数据库配置

项目使用 Docker Compose 来管理数据库，确保在启动应用前先启动数据库服务：

```bash
# 启动 MySQL 数据库
docker-compose up -d mysql

# 查看数据库状态
docker-compose ps

# 停止数据库
docker-compose down
```

## 配置文件示例

### .env.dev (开发环境)
```env
# 开发环境配置
PROJECT_NAME=AI Agents API (Dev)
VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# 服务器配置
HOST=127.0.0.1
PORT=8000
RELOAD=true

# 数据库配置 (与 docker-compose.yml 匹配)
# 确保 Docker 容器正在运行: docker-compose up -d mysql
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/ai_agents

# JWT配置
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 日志配置
LOG_LEVEL=DEBUG

# CORS配置 (开发环境允许本地访问)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000", "http://127.0.0.1:8080"]
```

## 注意事项

1. **开发环境**: 适用于所有开发和测试工作
2. **密钥管理**: 请确保使用安全的密钥
3. **数据库**: 使用 Docker 提供的 MySQL 数据库
4. **配置文件**: `.env.dev` 包含开发环境的标准配置 