#!/usr/bin/env python3
"""
AI Agents FastAPI 应用启动脚本
"""

import uvicorn
import os

if __name__ == "__main__":
    # 获取环境变量或使用默认值
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    print(f"🚀 启动 AI Agents API 服务...")
    print(f"📍 访问地址: http://{host}:{port}")
    print(f"📖 API文档: http://{host}:{port}/docs")
    print(f"🔄 热重载: {'开启' if reload else '关闭'}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    ) 