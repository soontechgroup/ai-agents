# Docker 容器化平台

## 📚 使用说明

项目使用 Docker 和 docker-compose 来管理数据库服务，确保开发环境的一致性。

## 🛠 Docker 安装

### macOS 安装
```bash
# 下载 Docker Desktop
# 访问 https://www.docker.com/products/docker-desktop

# 或使用 Homebrew
brew install --cask docker

# 验证安装
docker --version
docker-compose --version
```

### Linux 安装
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 添加用户到 docker 组
sudo usermod -aG docker $USER

# 安装 docker-compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

## 📝 Dockerfile 常用命令

### 基础命令
```dockerfile
# 基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 复制文件
COPY requirements.txt .
COPY . .

# 运行命令
RUN pip install -r requirements.txt

# 设置环境变量
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "run.py"]
```

### 命令说明
- `FROM` - 指定基础镜像
- `WORKDIR` - 设置工作目录
- `COPY` - 复制文件到镜像
- `RUN` - 执行命令（构建时）
- `ENV` - 设置环境变量
- `EXPOSE` - 声明容器端口
- `CMD` - 容器启动时执行的命令

## 🔧 项目使用

### 启动数据库服务
```bash
# 启动所有数据库
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs

# 停止服务
docker-compose down
```

### docker-compose.yml 配置
```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: ai-agents-mysql
    environment:
      MYSQL_ROOT_PASSWORD: 123456
      MYSQL_DATABASE: ai_agents
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    profiles:
      - db
      - all

  mongodb:
    image: mongo:7.0
    container_name: ai-agents-mongodb
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: password123
    ports:
      - "27018:27017"
    volumes:
      - mongodb_data:/data/db
    profiles:
      - db
      - all

  neo4j:
    image: neo4j:5.15
    container_name: ai-agents-neo4j
    environment:
      NEO4J_AUTH: neo4j/password123
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    profiles:
      - graph
      - all

  chromadb:
    image: chromadb/chroma:0.4.15
    container_name: ai-agents-chromadb
    ports:
      - "8000:8000"
    volumes:
      - chromadb_data:/chroma/chroma
    profiles:
      - vector
      - all

volumes:
  mysql_data:
  mongodb_data:
  neo4j_data:
  chromadb_data:
```

### Profile 使用
```bash
# 启动所有服务
docker-compose --profile all up -d

# 只启动数据库服务（MySQL + MongoDB）
docker-compose --profile db up -d

# 只启动图数据库
docker-compose --profile graph up -d

# 只启动向量数据库
docker-compose --profile vector up -d

# 启动多个 profile
docker-compose --profile db --profile vector up -d
```

### 常用命令
```bash
# 查看运行中的容器
docker ps

# 查看所有容器
docker ps -a

# 查看镜像
docker images

# 清理未使用的容器和镜像
docker system prune

# 查看容器日志
docker logs ai-agents-mysql

# 进入容器
docker exec -it ai-agents-mysql bash

# 重启服务
docker-compose restart mysql
```

### 数据库连接信息
- **MySQL**: `localhost:3306` (root/123456)
- **MongoDB**: `localhost:27018` (admin/password123)
- **Neo4j**: `localhost:7474` (neo4j/password123)

使用 Docker 可以快速搭建一致的开发环境，避免本地安装配置数据库的复杂性。