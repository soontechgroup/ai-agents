from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import mysql.connector
from mysql.connector.cursor import MySQLCursorDict
import os
from typing import List, Optional, Dict, Any, cast, Literal
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi.responses import JSONResponse

# Secret key for JWT
SECRET_KEY = "your-secret-key-keep-it-secret"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

router = APIRouter(prefix="/api/v1")

# Error Response Models
class ErrorDetail(BaseModel):
    detail: str
    error_code: str
    error_type: Literal["validation_error", "database_error", "auth_error", "server_error"]

class ErrorResponse(BaseModel):
    success: Literal[False] = False
    error: ErrorDetail

class SuccessResponse(BaseModel):
    success: Literal[True] = True

class UserCreate(BaseModel):
    username: str
    email: str
    password_hash: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None

class User(BaseModel):
    id: int
    username: str
    email: str
    password_hash: str
    created_at: str

class Token(SuccessResponse):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

class LoginResponse(SuccessResponse):
    access_token: str
    token_type: str
    user: UserResponse

class UserAuth(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

def get_db_connection():
    try:
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        database = os.getenv("DB_NAME")
        if not all([host, port, user, password, database]):
            raise ValueError("Missing one or more required environment variables for DB connection.")
        conn = mysql.connector.connect(
            host=host,
            port=int(str(port)),
            user=user,
            password=password,
            database=database,
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub", 0))
        if user_id == 0:
            raise HTTPException(
                status_code=401,
                detail={
                    "success": False,
                    "error": {
                        "detail": "Invalid authentication token",
                        "error_code": "INVALID_TOKEN",
                        "error_type": "auth_error"
                    }
                }
            )
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {
                    "detail": "Could not validate token",
                    "error_code": "TOKEN_VALIDATION_FAILED",
                    "error_type": "auth_error"
                }
            }
        )
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = cast(MySQLCursorDict, conn.cursor(dictionary=True))
        cursor.execute("SELECT id, username as name, email FROM user WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "success": False,
                    "error": {
                        "detail": "User not found",
                        "error_code": "USER_NOT_FOUND",
                        "error_type": "auth_error"
                    }
                }
            )
        
        return cast(Dict[str, Any], user)
        
    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": {
                    "detail": f"Database error: {str(e)}",
                    "error_code": "DB_ERROR",
                    "error_type": "database_error"
                }
            }
        )
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@router.post("/users", response_model=User)
def create_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO user (username, email, password_hash) VALUES (%s, %s, %s)",
            (user.username, user.email, user.password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        cursor.execute("SELECT id, username, email, password_hash, created_at FROM user WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found after creation")
        def safe_int(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: id is None")
            return int(val) if not isinstance(val, int) else val
        def safe_str(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: username is None")
            return str(val) if not isinstance(val, str) else val
        def safe_iso(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: created_at is None")
            return val.isoformat() if hasattr(val, "isoformat") else str(val)
        if not isinstance(row, tuple) or len(row) < 5 or any(x is None for x in (row[0], row[1], row[2], row[3], row[4])):
            raise HTTPException(status_code=500, detail="Malformed user row from database (None value found)")
        return User(
            id=safe_int(row[0]),
            username=safe_str(row[1]),
            email=safe_str(row[2]),
            password_hash=safe_str(row[3]),
            created_at=safe_iso(row[4])
        )
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.get("/users", response_model=List[User])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password_hash, created_at FROM user")
    users = []
    for row in cursor.fetchall():
        if row is not None:
            if not isinstance(row, tuple) or len(row) < 5 or any(x is None for x in (row[0], row[1], row[2], row[3], row[4])):
                raise HTTPException(status_code=500, detail="Malformed user row from database (None value found)")
            def safe_int(val):
                if val is None:
                    raise HTTPException(status_code=500, detail="Malformed user row: id is None")
                return int(val) if not isinstance(val, int) else val
            def safe_str(val, field_name):
                if val is None:
                    raise HTTPException(status_code=500, detail=f"Malformed user row: {field_name} is None")
                return str(val) if not isinstance(val, str) else val
            def safe_iso(val):
                if val is None:
                    raise HTTPException(status_code=500, detail="Malformed user row: created_at is None")
                return val.isoformat() if hasattr(val, "isoformat") else str(val)
            users.append(User(
                id=safe_int(row[0]),
                username=safe_str(row[1], "username"),
                email=safe_str(row[2], "email"),
                password_hash=safe_str(row[3], "password_hash"),
                created_at=safe_iso(row[4])
            ))
    conn.close()
    return users

@router.get("/users/{user_id}", response_model=User)
def get_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, password_hash, created_at FROM user WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        def safe_int(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: id is None")
            return int(val) if not isinstance(val, int) else val
        def safe_str(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: username is None")
            return str(val) if not isinstance(val, str) else val
        def safe_iso(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: created_at is None")
            return val.isoformat() if hasattr(val, "isoformat") else str(val)
        if not isinstance(row, tuple) or len(row) < 5 or any(x is None for x in (row[0], row[1], row[2], row[3], row[4])):
            raise HTTPException(status_code=500, detail="Malformed user row from database (None value found)")
        return User(
            id=safe_int(row[0]),
            username=safe_str(row[1]),
            email=safe_str(row[2]),
            password_hash=safe_str(row[3]),
            created_at=safe_iso(row[4])
        )
    else:
        raise HTTPException(status_code=404, detail="User not found")

@router.put("/users/{user_id}", response_model=User)
def update_user(user_id: int, user: UserUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user WHERE id = %s", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    fields = []
    values = []
    if user.username is not None:
        fields.append("username = %s")
        values.append(user.username)
    if user.email is not None:
        fields.append("email = %s")
        values.append(user.email)
    if user.password_hash is not None:
        fields.append("password_hash = %s")
        values.append(user.password_hash)
    if not fields:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    values.append(user_id)
    try:
        cursor.execute(f"UPDATE user SET {', '.join(fields)} WHERE id = %s", tuple(values))
        conn.commit()
        cursor.execute("SELECT id, username, email, password_hash, created_at FROM user WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found after update")
        def safe_int(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: id is None")
            return int(val) if not isinstance(val, int) else val
        def safe_str(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: username is None")
            return str(val) if not isinstance(val, str) else val
        def safe_iso(val):
            if val is None:
                raise HTTPException(status_code=500, detail="Malformed user row: created_at is None")
            return val.isoformat() if hasattr(val, "isoformat") else str(val)
        if not isinstance(row, tuple) or len(row) < 5 or any(x is None for x in (row[0], row[1], row[2], row[3], row[4])):
            raise HTTPException(status_code=500, detail="Malformed user row from database (None value found)")
        return User(
            id=safe_int(row[0]),
            username=safe_str(row[1]),
            email=safe_str(row[2]),
            password_hash=safe_str(row[3]),
            created_at=safe_iso(row[4])
        )
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user WHERE id = %s", (user_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    try:
        cursor.execute("DELETE FROM user WHERE id = %s", (user_id,))
        conn.commit()
        return {"detail": "User deleted"}
    except mysql.connector.Error as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@router.get("/")
def read_root():
    db_port = os.getenv("DB_PORT")
    if db_port is None:
        raise HTTPException(status_code=500, detail="Missing DB_PORT environment variable")
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(db_port),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user")
    users = cursor.fetchall()
    conn.close()
    return {"users": users}

@router.post("/auth/register", response_model=Token, responses={
    400: {"model": ErrorResponse, "description": "Registration failed"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def register(user: UserAuth):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM user WHERE email = %s", (user.email,))
        if cursor.fetchone():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": {
                        "detail": "Email already registered",
                        "error_code": "EMAIL_EXISTS",
                        "error_type": "validation_error"
                    }
                }
            )
        
        # Hash the password
        hashed_password = pwd_context.hash(user.password)
        
        # Insert new user
        cursor.execute(
            "INSERT INTO user (username, email, password_hash) VALUES (%s, %s, %s)",
            (user.name, user.email, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        # Create access token
        access_token = create_access_token({"sub": str(user_id)})
        
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except mysql.connector.Error as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "detail": f"Database error: {str(e)}",
                    "error_code": "DB_ERROR",
                    "error_type": "database_error"
                }
            }
        )
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "detail": f"Registration failed: {str(e)}",
                    "error_code": "REGISTRATION_FAILED",
                    "error_type": "server_error"
                }
            }
        )
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@router.post("/auth/login", response_model=LoginResponse, responses={
    400: {"model": ErrorResponse, "description": "Login failed"},
    401: {"model": ErrorResponse, "description": "Invalid credentials"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def login(user: UserLogin):
    conn = None
    try:
        conn = get_db_connection()
        cursor = cast(MySQLCursorDict, conn.cursor(dictionary=True))
        
        # Get user by email
        cursor.execute("SELECT id, username as name, email, password_hash as password FROM user WHERE email = %s", (user.email,))
        result = cursor.fetchone()
        
        if not result:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "detail": "Invalid email or password",
                        "error_code": "INVALID_CREDENTIALS",
                        "error_type": "auth_error"
                    }
                }
            )
        
        # Verify password
        stored_password = str(result['password'])
        if not pwd_context.verify(user.password, stored_password):
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "detail": "Invalid email or password",
                        "error_code": "INVALID_CREDENTIALS",
                        "error_type": "auth_error"
                    }
                }
            )
        
        # Create access token
        user_id = str(result['id'])
        access_token = create_access_token({"sub": user_id})
        
        # Return both token and user data
        return {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": result['id'],
                "name": result['name'],
                "email": result['email']
            }
        }
        
    except mysql.connector.Error as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "detail": f"Database error: {str(e)}",
                    "error_code": "DB_ERROR",
                    "error_type": "database_error"
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": {
                    "detail": f"Login failed: {str(e)}",
                    "error_code": "LOGIN_FAILED",
                    "error_type": "server_error"
                }
            }
        )
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@router.get("/auth/me", response_model=UserResponse, responses={
    401: {"model": ErrorResponse, "description": "Authentication failed"},
    404: {"model": ErrorResponse, "description": "User not found"},
    500: {"model": ErrorResponse, "description": "Server error"}
})
async def get_user_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        return {
            "success": True,
            "id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "detail": f"Failed to get user info: {str(e)}",
                    "error_code": "USER_INFO_FAILED",
                    "error_type": "server_error"
                }
            }
        )