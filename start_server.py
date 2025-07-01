#!/usr/bin/env python3
"""
AI Agents 系统启动脚本
包含JWT认证和用户管理功能
"""

import uvicorn
import os

def print_startup_info():
    """打印启动信息"""
    print("=" * 50)
    print("🚀 AI Agents 系统启动中...")
    print("=" * 50)
    print()

    # 检查JWT密钥
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret or jwt_secret == "your-super-secret-jwt-key-abc123456":
        print("⚠️  警告: 使用默认的JWT密钥，生产环境中请更改!")
        print("   建议设置环境变量: export JWT_SECRET_KEY='your-secure-key'")
        print()

    # 检查数据库连接
    db_url = os.getenv("DATABASE_URL", "mysql+pymysql://root:Kevinisagod1.1@localhost:3306/userdb?charset=utf8mb4")
    print(f"📊 数据库连接: {db_url.split('@')[1] if '@' in db_url else 'local'}")
    print()

    # 服务器配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    print(f"🌐 服务器地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    print(f"📖 ReDoc文档: http://{host}:{port}/redoc")
    print()

    print("🔑 可用的API端点:")
    print("   POST /api/v1/auth/register  - 用户注册")
    print("   POST /api/v1/auth/login     - 用户登录")
    print("   GET  /api/v1/auth/me        - 获取当前用户信息")
    print("   POST /api/v1/auth/refresh   - 刷新令牌")
    print("   GET  /api/v1/user           - 获取用户列表")
    print("   GET  /api/v1/protected/*    - 受保护的接口")
    print()

    print("💡 测试建议:")
    print("   1. 先访问 http://localhost:8000/docs 查看API文档")
    print("   2. 运行测试脚本: python test_jwt_api.py")
    print("   3. 访问用户管理界面: http://localhost:8000/static/user.html")
    print("   4. 使用Postman或curl测试API接口")
    print()

    print("🎯 按 Ctrl+C 停止服务器")
    print("=" * 50)

def main():
    """主函数"""
    print_startup_info()

    # 服务器配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))

    try:
        # 启动服务器
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=["app/"],
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")

if __name__ == "__main__":
    main() 