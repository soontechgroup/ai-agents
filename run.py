#!/usr/bin/env python3
"""
PyCharm 开发环境启动脚本
支持通过命令行参数指定环境
使用方法：
    python run.py                    # 默认开发环境
    python run.py --env dev          # 开发环境
"""

import uvicorn
import os
import argparse

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="FastAPI AI Agents 启动脚本")
    parser.add_argument(
        "--env", 
        type=str, 
        default="dev",
        choices=["dev", "development"],
        help="指定运行环境 (默认: dev)"
    )
    parser.add_argument(
        "--host", 
        type=str, 
        default="127.0.0.1",
        help="服务器主机地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="服务器端口 (默认: 8000)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true",
        help="启用热重载 (默认: True)"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    # 设置环境变量
    os.environ["ENVIRONMENT"] = args.env
    
    # 从环境变量或命令行参数获取配置
    host = args.host
    port = args.port
    reload = args.reload or True  # 开发模式默认开启热重载
    
    print("\n🔧 PyCharm 开发模式启动...")
    print(f"🌍 运行环境: {args.env}")
    print(f"📍 访问地址: http://{host}:{port}")
    print(f"📖 API文档: http://{host}:{port}/docs")
    print(f"🔄 热重载: {'开启' if reload else '关闭'}")
    print("=" * 50)
    
    # 启动开发服务器
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
        access_log=True  # 显示访问日志
    ) 