# Passlib 密码哈希库

## 📚 使用说明

项目使用 Passlib 进行安全的密码哈希和验证，提供现代化的密码保护机制。

## 🛠 框架配置

### 安装依赖
```bash
pip install passlib[bcrypt]
```

### 基本配置
```python
from passlib.context import CryptContext

# 配置密码上下文
pwd_context = CryptContext(
    schemes=["bcrypt"],    # 使用bcrypt算法
    deprecated="auto",     # 自动标记过时算法
    bcrypt__rounds=12      # 工作因子
)

# 哈希密码
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 验证密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

## 💻 项目应用

### 密码服务
```python
# app/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthenticationService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
```

### 用户注册和认证
```python
# app/services/user_service.py
class UserService:
    async def create_user(self, email: str, password: str):
        # 哈希密码
        hashed_password = AuthenticationService.get_password_hash(password)

        # 创建用户
        user_data = {
            "email": email,
            "hashed_password": hashed_password,
        }
        return await self.user_repository.create(user_data)

    async def authenticate_user(self, email: str, password: str):
        user = await self.user_repository.get_by_email(email)
        if not user:
            return None

        # 验证密码
        if not AuthenticationService.verify_password(password, user.hashed_password):
            return None

        return user
```

### 密码验证器
```python
# app/validators/password_validator.py
class PasswordValidator:
    MIN_LENGTH = 8

    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, list[str]]:
        errors = []

        if len(password) < cls.MIN_LENGTH:
            errors.append(f"密码长度至少需要 {cls.MIN_LENGTH} 个字符")

        if not any(c.isupper() for c in password):
            errors.append("密码必须包含大写字母")

        if not any(c.islower() for c in password):
            errors.append("密码必须包含小写字母")

        if not any(c.isdigit() for c in password):
            errors.append("密码必须包含数字")

        return len(errors) == 0, errors
```

Passlib 为项目提供安全的密码哈希和验证功能，防止密码泄露和攻击。