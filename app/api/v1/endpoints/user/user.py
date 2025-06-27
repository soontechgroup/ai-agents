from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import mysql.connector
from mysql.connector.cursor import MySQLCursorDict
import os
from typing import List, Optional, Dict, Any, cast
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Secret key for JWT
SECRET_KEY = "your-secret-key-keep-it-secret"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

class LoginResponse(BaseModel):
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

@app.post("/users", response_model=User)
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

@app.get("/users", response_model=List[User])
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

@app.get("/users/{user_id}", response_model=User)
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

@app.put("/users/{user_id}", response_model=User)
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

@app.delete("/users/{user_id}")
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

@app.get("/")
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
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate token")
    
    conn = get_db_connection()
    cursor = cast(MySQLCursorDict, conn.cursor(dictionary=True))
    cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return cast(Dict[str, Any], user)

@app.post("/auth/register", response_model=Token)
async def register(user: UserAuth):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if email already exists
    cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash the password
    hashed_password = pwd_context.hash(user.password)
    
    try:
        # Insert new user
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (user.name, user.email, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid
        
        # Create access token
        access_token = create_access_token({"sub": str(user_id)})
        
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.post("/auth/login", response_model=LoginResponse)
async def login(user: UserLogin):
    conn = get_db_connection()
    cursor = cast(MySQLCursorDict, conn.cursor(dictionary=True))
    
    # Get user by email
    cursor.execute("SELECT id, name, email, password FROM users WHERE email = %s", (user.email,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    stored_password = str(result['password'])
    if not pwd_context.verify(user.password, stored_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create access token
    user_id = str(result['id'])
    access_token = create_access_token({"sub": user_id})
    
    # Return both token and user data
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": result['id'],
            "name": result['name'],
            "email": result['email']
        }
    }

@app.get("/auth/me", response_model=UserResponse)
async def get_user_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user