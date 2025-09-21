# Python 3.12+ 环境安装与管理

## 📚 环境说明

项目使用 Python 3.12+ 版本，推荐使用 Miniconda 管理 Python 环境，确保开发环境的一致性和隔离性。

## 🛠 Miniconda 安装

### 各平台安装指南

#### macOS 安装
```bash
# 下载 Miniconda 安装包
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh

# 或使用 curl
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh

# 运行安装脚本
bash Miniconda3-latest-MacOSX-x86_64.sh

# 按提示完成安装，重启终端或执行
source ~/.bashrc
# 或
source ~/.zshrc
```

#### Linux 安装
```bash
# 下载安装包
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# 运行安装脚本
bash Miniconda3-latest-Linux-x86_64.sh

# 重新加载配置
source ~/.bashrc

# 验证安装
conda --version
```

## 🔧 环境管理
```bash
# 创建 Python 3.12 环境
conda create -n ai-agents python=3.12

# 激活环境
conda activate ai-agents

# 查看当前环境
conda info --envs

# 列出环境中的包
conda list

# 更新 conda 本身
conda update conda

# 更新环境中的所有包
conda update --all

# 删除环境
conda env remove -n ai-agents
```

### 项目环境配置
```bash
# 创建项目环境
conda create -n ai-agents python=3.12

# 激活环境
conda activate ai-agents

# 安装基础开发工具
pip install --upgrade pip
pip install wheel setuptools

# 安装项目依赖
pip install -r requirements.txt
```


## 💻 项目应用

### 1. 快速开始指南
```bash
# 克隆项目
git clone <project-repo>
cd ai-agents

# 创建并激活环境
conda create -n ai-agents python=3.12
conda activate ai-agents

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env.dev
# 编辑 .env.dev 配置数据库连接等

# 启动服务
python run.py --env dev --reload
```

### 2. 项目结构
```
ai-agents/
├── app/                    # 应用核心代码
│   ├── api/               # API 路由
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   ├── services/          # 业务服务
│   └── repositories/      # 数据访问层
├── tests/                 # 测试代码
├── docs/                  # 项目文档
├── alembic/               # 数据库迁移
├── requirements.txt       # Python 依赖
├── .env.dev              # 开发环境配置
├── run.py                # 应用启动入口
└── docker-compose.yml    # Docker 服务配置
```

### 3. 环境变量配置
```bash
# .env.dev - 开发环境配置示例
# Python 环境配置
PYTHONPATH=.

# 数据库配置
DATABASE_URL=mysql+pymysql://root:123456@localhost:3306/ai_agents
MONGODB_URL=mongodb://admin:password123@localhost:27018/ai_agents
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# ChromaDB 配置
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# OpenAI 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4

# 应用配置
SECRET_KEY=your_secret_key
DEBUG=true
LOG_LEVEL=INFO
```

### 4. 常用开发命令
```bash
# 激活环境
conda activate ai-agents

# 启动开发服务器
python run.py --env dev --reload

# 数据库迁移
alembic upgrade head

# 运行测试
pytest

# 查看依赖
pip list
conda list

# 更新依赖文件
pip freeze > requirements.txt

# 导出 conda 环境
conda env export > environment.yml
```

使用 Miniconda 可以确保项目开发环境的一致性，避免依赖冲突，提高团队协作效率。