#!/usr/bin/env python3
"""
PyCharm 开发环境启动脚本
仅用于开发调试，生产环境请使用 run.sh
"""

import uvicorn
import os

if __name__ == "__main__":
    # 开发环境配置
    host = os.getenv("HOST", "127.0.0.1")  # 开发环境默认本地访问
    port = int(os.getenv("PORT", 8000))
    
    print("🔧 PyCharm 开发模式启动...")
    print(f"📍 访问地址: http://{host}:{port}")
    print(f"📖 API文档: http://{host}:{port}/docs")
    print("🔄 热重载: 开启")
    print("=" * 50)
    
    # 启动开发服务器
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,  # 开发模式始终开启热重载
        log_level="info",
        access_log=True  # 显示访问日志
    ) 