import os

try:
    import mysql.connector
except ImportError:  # pragma: no cover - optional dependency guard
    mysql = None
else:
    mysql = mysql.connector

DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASS = os.getenv("MYSQL_PASSWORD", "Root@2024!")
DB_NAME = os.getenv("MYSQL_DATABASE", "Big_db")


def get_connection():
    if mysql is None:
        raise RuntimeError("mysql-connector-python is not installed")
    return mysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
    )

    


