# 环境配置说明

## 概述

本项目支持多环境配置，可以通过环境变量或命令行参数指定不同的运行环境。

## 支持的环境

- `dev` / `development` - 开发环境 (默认)
- `test` - 测试环境
- `staging` - 预发环境
- `prod` / `production` - 生产环境

## 配置文件

每个环境对应一个配置文件：

- `.env.dev` - 开发环境配置
- `.env.test` - 测试环境配置
- `.env.staging` - 预发环境配置
- `.env.prod` - 生产环境配置
- `.env` - 默认配置文件（备用）

## 使用方法

### 1. 使用 Python 启动脚本

```bash
# 默认开发环境
python run.py

# 指定环境
python run.py --env dev
python run.py --env staging
python run.py --env prod

# 指定其他参数
python run.py --env prod --host 0.0.0.0 --port 9000
```

### 2. 使用 Shell 脚本

```bash
# 默认开发环境
./scripts/run.sh start

# 指定环境
ENVIRONMENT=dev ./scripts/run.sh start
ENVIRONMENT=staging ./scripts/run.sh start
ENVIRONMENT=prod ./scripts/run.sh start

# 开发模式
ENVIRONMENT=dev ./scripts/run.sh dev
```

### 3. 直接设置环境变量

```bash
# 设置环境变量
export ENVIRONMENT=prod

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

### .env.staging (预发环境)
```env
# 预发环境配置
PROJECT_NAME=AI Agents API (Staging)
ENVIRONMENT=staging
DEBUG=false

HOST=0.0.0.0
PORT=8000
RELOAD=false

DATABASE_URL=mysql+pymysql://username:password@localhost:3306/ai_agents_staging
SECRET_KEY=staging-secret-key-please-change-this
LOG_LEVEL=INFO

CORS_ORIGINS=["https://staging.your-domain.com"]
```

### .env.prod (生产环境)
```env
# 生产环境配置
PROJECT_NAME=AI Agents API
ENVIRONMENT=production
DEBUG=false

HOST=0.0.0.0
PORT=8000
RELOAD=false

DATABASE_URL=mysql+pymysql://username:password@localhost:3306/ai_agents_prod
SECRET_KEY=your-super-secret-key-for-production-please-change-this
LOG_LEVEL=INFO

CORS_ORIGINS=["https://your-frontend-domain.com"]
```

## 环境变量优先级

1. 命令行参数 (最高优先级)
2. 环境变量文件 (.env.dev, .env.prod 等)
3. 系统环境变量
4. 默认配置值 (最低优先级)

## 注意事项

1. **安全性**: 生产环境的配置文件不应该提交到版本控制系统
2. **密钥管理**: 每个环境应该使用不同的密钥和密码
3. **数据库**: 不同环境应该使用不同的数据库
4. **调试模式**: 生产环境应该关闭调试模式
5. **CORS**: 生产环境应该配置正确的前端域名

## 故障排除

如果环境配置文件不存在，系统会：
1. 显示警告信息
2. 尝试加载默认的 `.env` 文件
3. 使用代码中的默认配置值

启动时会显示当前的环境信息：
```
🔧 加载环境配置文件: .env.dev
🚀 当前运行环境: dev
📊 调试模式: 开启
🔗 数据库连接: mysql+pymysql://root:123456@localhost:3306/ai_agents_dev
``` 
