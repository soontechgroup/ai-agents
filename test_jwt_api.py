import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000/api/v1"

def test_register():
    """测试用户注册"""
    print("=== 测试用户注册 ===")
    
    register_data = {
        "name": "测试用户",
        "email": "test@example.com",
        "gender": "男",
        "password": "123456"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 注册成功!")
            print(f"👤 用户名: {result['user_info']['name']}")
            print(f"📧 邮箱: {result['user_info']['email']}")
            print(f"🔑 访问令牌: {result['access_token'][:50]}...")
            return result['access_token']
        else:
            print(f"❌ 注册失败: {response.json()}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None

def test_login():
    """测试用户登录"""
    print("\n=== 测试用户登录 ===")
    
    login_data = {
        "email": "test@example.com",
        "password": "123456"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 登录成功!")
            print(f"👤 用户名: {result['user_info']['name']}")
            print(f"📧 邮箱: {result['user_info']['email']}")
            print(f"🔑 访问令牌: {result['access_token'][:50]}...")
            return result['access_token']
        else:
            print(f"❌ 登录失败: {response.json()}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None

def test_get_current_user(token):
    """测试获取当前用户信息"""
    print("\n=== 测试获取当前用户信息 ===")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 获取用户信息成功!")
            print(f"👤 用户名: {result['name']}")
            print(f"📧 邮箱: {result['email']}")
            print(f"👥 性别: {result['gender']}")
        else:
            print(f"❌ 获取用户信息失败: {response.json()}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")

def test_protected_profile(token):
    """测试受保护的个人资料接口"""
    print("\n=== 测试受保护的个人资料接口 ===")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/protected/profile", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 获取个人资料成功!")
            print(f"👤 用户名: {result['name']}")
            print(f"📧 邮箱: {result['email']}")
            print(f"👥 性别: {result['gender']}")
        else:
            print(f"❌ 获取个人资料失败: {response.json()}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")

def test_update_protected_profile(token):
    """测试更新受保护的个人资料"""
    print("\n=== 测试更新受保护的个人资料 ===")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    update_data = {
        "name": "更新后的用户名",
        "gender": "女"
    }
    
    try:
        response = requests.put(f"{BASE_URL}/protected/profile", json=update_data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 更新资料成功!")
            print(f"👤 新姓名: {result['name']}")
            print(f"👥 新性别: {result['gender']}")
        else:
            print(f"❌ 更新资料失败: {response.json()}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")

def test_refresh_token(token):
    """测试刷新令牌"""
    print("\n=== 测试刷新令牌 ===")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/refresh", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 刷新令牌成功!")
            print(f"🔑 新访问令牌: {result['access_token'][:50]}...")
            return result['access_token']
        else:
            print(f"❌ 刷新令牌失败: {response.json()}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
        return None

def test_invalid_token():
    """测试无效令牌"""
    print("\n=== 测试无效令牌 ===")
    
    headers = {
        "Authorization": "Bearer invalid-token"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        
        if response.status_code == 401:
            print("✅ 无效令牌被正确拒绝!")
            print(f"🔒 错误信息: {response.json()['detail']}")
        else:
            print(f"❌ 预期401错误，但得到: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")

def main():
    """主测试函数"""
    print("🚀 开始JWT API测试")
    print("=" * 50)
    
    # 测试注册（如果失败则尝试登录）
    token = test_register()
    
    if not token:
        # 注册失败，尝试登录
        token = test_login()
    
    if not token:
        print("❌ 无法获取访问令牌，测试终止")
        return
    
    # 测试各种认证相关的API
    test_get_current_user(token)
    test_protected_profile(token)
    test_update_protected_profile(token)
    
    # 测试刷新令牌
    new_token = test_refresh_token(token)
    if new_token:
        token = new_token
    
    # 测试无效令牌
    test_invalid_token()
    
    print("\n" + "=" * 50)
    print("🎉 JWT API测试完成!")

if __name__ == "__main__":
    main() 