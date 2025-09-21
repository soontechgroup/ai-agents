# FastAPI Web 框架

## 📚 使用说明

项目使用 FastAPI 作为 Web 框架，提供异步、高性能的 API 服务。

## 🛠 框架配置

### 安装依赖
```bash
pip install fastapi uvicorn
```

### 基本配置
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Agents API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```


## 💻 项目应用

### 路由组织
```python
# app/api/v1/endpoints/digital_humans.py
from fastapi import APIRouter, Depends
from typing import List

router = APIRouter()

@router.post("/create")
async def create_digital_human(
    digital_human_data: DigitalHumanCreate,
    current_user: User = Depends(get_current_active_user)
):
    # 创建数字人逻辑
    return {"message": "数字人创建成功"}

@router.get("/list")
async def list_digital_humans(
    current_user: User = Depends(get_current_active_user)
):
    # 获取数字人列表
    return {"digital_humans": []}
```

### 流式响应（SSE）
```python
from sse_starlette.sse import EventSourceResponse

@router.post("/train/stream")
async def train_digital_human_stream(
    request: DigitalHumanTrainRequest,
    current_user: User = Depends(get_current_active_user)
):
    async def generate():
        # 流式生成训练响应
        yield f"data: 训练开始\n\n"
        yield f"data: 训练完成\n\n"

    return EventSourceResponse(generate())
```

### 依赖注入
```python
# app/dependencies/services.py
from fastapi import Depends
from sqlalchemy.orm import Session

def get_digital_human_service(db: Session = Depends(get_db)):
    return DigitalHumanService(db)

# 在路由中使用
@router.post("/create")
async def create_digital_human(
    data: DigitalHumanCreate,
    service: DigitalHumanService = Depends(get_digital_human_service)
):
    return service.create(data)
```

### 服务器启动（Uvicorn）
```python
# run.py - 项目启动脚本
import uvicorn
import argparse

def run_server(env: str = "dev", host: str = "0.0.0.0", port: int = 8000):
    config = {
        "app": "app.main:app",
        "host": host,
        "port": port,
        "reload": env == "dev",
        "log_level": "info",
    }

    if env == "dev":
        config.update({
            "reload_dirs": ["app"],
        })

    if env == "prod":
        config.update({
            "workers": 4,
            "loop": "uvloop",
            "http": "httptools",
        })

    uvicorn.run(**config)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="dev", choices=["dev", "prod"])
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    run_server(args.env, args.host, args.port)
```

FastAPI 配合 Uvicorn 为项目提供异步、高性能的 Web API 框架。