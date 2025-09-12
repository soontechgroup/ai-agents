"""
Loguru 日志配置模块
提供统一的日志配置和管理
"""

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

# 统一的日志格式（包含完整路径，支持 PyCharm 点击跳转）
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
    """配置日志系统"""
    
    # 控制台输出（彩色）
    # 直接使用带完整路径的格式，PyCharm 会自动识别
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,  # 统一格式，包含完整路径
        level=settings.LOG_LEVEL.upper(),
        colorize=True,
        enqueue=True,  # 异步日志
        backtrace=False,  # 不显示完整堆栈
        diagnose=False,  # 不显示变量值
    )
    
    # 所有日志文件
    logger.add(
        LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        format=LOG_FORMAT,
        level="DEBUG",
        rotation=settings.LOG_ROTATION,  # 使用配置的轮转策略
        retention=settings.LOG_RETENTION,  # 使用配置的保留时间
        compression="zip",  # 压缩旧文件
        enqueue=True,
        encoding="utf-8",
        backtrace=False,
        diagnose=False,  # 文件中不显示变量值（安全考虑）
    )
    
    # 错误日志文件（单独记录）
    logger.add(
        LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        format=LOG_FORMAT,
        level="ERROR",
        rotation=settings.LOG_ROTATION,
        retention="90 days",  # 错误日志保留更久
        compression="zip",
        enqueue=True,
        encoding="utf-8",
        backtrace=False,
        diagnose=False,  # 简化错误日志
    )
    
    # 添加请求日志（仅在生产环境）
    if not settings.DEBUG:
        logger.add(
            LOG_DIR / "access_{time:YYYY-MM-DD}.log",
            format=LOG_FORMAT,
            level="INFO",
            rotation="500 MB",  # 按大小轮转
            retention="7 days",  # 访问日志保留7天
            compression="zip",
            enqueue=True,
            encoding="utf-8",
            filter=lambda record: "request" in record["extra"],
        )
    
    logger.info("Loguru 日志系统初始化完成")
    logger.info(f"日志级别: {settings.LOG_LEVEL}")
    logger.info(f"日志目录: {LOG_DIR.absolute()}")
    logger.info(f"调试模式: {'开启' if settings.DEBUG else '关闭'}")


def get_request_id() -> str:
    """获取当前请求ID"""
    return request_id_var.get()


def set_request_id(request_id: str = None) -> str:
    """设置请求ID"""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


class InterceptHandler:
    """
    拦截标准 logging 模块的日志
    将其重定向到 loguru
    """
    
    def __init__(self, level="INFO"):
        self.level = level
    
    def write(self, message):
        """拦截日志消息"""
        if message.strip():
            logger.opt(depth=2).log(self.level, message.strip())


def intercept_standard_logging():
    """
    拦截标准库和第三方库的日志
    统一使用 loguru 处理
    """
    import logging
    
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # 获取对应的 loguru 级别
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            
            # 查找调用者
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
    
    # 拦截 sqlalchemy 日志（如果需要）
    if settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


# 初始化日志系统
setup_logger()
intercept_standard_logging()

# 导出 logger 实例
__all__ = ["logger", "get_request_id", "set_request_id"]