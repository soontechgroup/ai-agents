import os
import mysql.connector
from mysql.connector.cursor import MySQLCursorDict
from fastapi import HTTPException

def get_db_connection():
    """Get a database connection with environment variables"""
    try:
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "3307")
        user = os.getenv("DB_USER", "root")
        password = os.getenv("DB_PASSWORD", "123456")
        database = os.getenv("DB_NAME", "ai_agents")
        
        if not all([host, port, user, database]):
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