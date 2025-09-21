# Loguru 日志库

## 📚 使用说明

项目使用 Loguru 进行日志记录，提供简洁的配置和强大的功能。

## 💻 项目应用

### 项目日志配置
```python
# app/core/logger.py
import sys
import os
from pathlib import Path
from loguru import logger
from app.core.config import settings
import uuid
from contextvars import ContextVar

# 创建请求ID上下文变量
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# 移除默认的日志处理器
logger.remove()

# 统一的日志格式（支持 PyCharm 点击跳转）
LOG_FORMAT = (
    "<green>{time:HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    'File "<cyan>{file.path}</cyan>", line <cyan>{line}</cyan>, in <cyan>{function}</cyan> | '
    "<level>{message}</level>"
)

# 创建日志目录
LOG_DIR = Path(settings.LOG_PATH)
LOG_DIR.mkdir(exist_ok=True)

def setup_logger():
    # 控制台输出（彩色）
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level=settings.LOG_LEVEL.upper(),
        colorize=True,
        enqueue=True,  # 异步日志
        backtrace=False,
        diagnose=False,
    )

    # 所有日志文件
    logger.add(
        LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        format=LOG_FORMAT,
        level="DEBUG",
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip",
        enqueue=True,
        encoding="utf-8",
        backtrace=False,
        diagnose=False,
    )

    # 错误日志文件（单独记录）
    logger.add(
        LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        format=LOG_FORMAT,
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention="90 days",
        compression="zip",
        enqueue=True,
        encoding="utf-8",
        backtrace=False,
        diagnose=False,
    )

    logger.info("Loguru 日志系统初始化完成")

# 初始化日志系统
setup_logger()
```

### 请求ID管理
```python
# app/core/logger.py
def get_request_id() -> str:
    """获取当前请求ID"""
    return request_id_var.get()

def set_request_id(request_id: str = None) -> str:
    """设置请求ID"""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id
```

### API请求日志中间件
```python
# app/main.py
from fastapi import Request
import time
from app.core.logger import logger, set_request_id

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    request_id = set_request_id()

    logger.bind(request_id=request_id).info(f"📥 [{request_id}] 收到请求: {request.method} {request.url.path}")

    if request.url.query:
        logger.bind(request_id=request_id).debug(f"查询参数: {request.url.query}")

    if settings.DEBUG:
        logger.bind(request_id=request_id).debug(f"请求头: {dict(request.headers)}")

    try:
        response = await call_next(request)

        process_time = time.time() - start_time

        logger.bind(request_id=request_id).info(
            f"✅ [{request_id}] 请求完成: {response.status_code} - {process_time:.3f}s"
        )

        return response

    except Exception as e:
        process_time = time.time() - start_time

        logger.bind(request_id=request_id).error(
            f"❌ [{request_id}] 请求失败: {str(e)} - {process_time:.3f}s"
        )
        logger.bind(request_id=request_id).error(traceback.format_exc())

        raise
```

### 标准日志拦截
```python
# app/core/logger.py
def intercept_standard_logging():
    """
    拦截标准库和第三方库的日志
    统一使用 loguru 处理
    """
    import logging

    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # 设置拦截处理器
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 拦截 uvicorn 日志
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

# 初始化拦截
intercept_standard_logging()
```

### 全局异常处理
```python
# app/main.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = get_request_id()

    logger.bind(request_id=request_id).error(
        f"❌ [{request_id}] 未处理异常: {type(exc).__name__}: {str(exc)}"
    )
    logger.bind(request_id=request_id).error(traceback.format_exc())

    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "内部服务器错误",
            "data": None
        }
    )
```

### 常用日志操作
```python
# 基本日志记录
logger.info("Information message")
logger.warning("Warning message")
logger.error("Error message")
logger.success("Success message")
logger.debug("Debug message")

# 带请求ID的日志
from app.core.logger import logger, get_request_id

request_id = get_request_id()
logger.bind(request_id=request_id).info(f"[{request_id}] 处理请求")

# 结构化日志
logger.info("用户操作", user_id=123, action="login", ip="192.168.1.1")

# 带上下文的日志
with logger.contextualize(user_id=123, operation="create"):
    logger.info("开始创建数字人")

# 异常捕获装饰器
@logger.catch
def risky_function():
    # 任何异常都会被自动记录
    pass
```

Loguru 为项目提供了简洁强大的日志解决方案，所有日志统一管理，支持请求追踪和异步处理。