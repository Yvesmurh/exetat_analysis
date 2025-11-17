import os 
import mysql.connector
from mysql.connector import errorcode

DB_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
DB_USER = os.getenv("MYSQL_USER", "root")
DB_PASS = os.getenv("MYSQL_PASSWORD", "Root@2024!")
DB_NAME = os.getenv("MYSQL_DATABASE", "exetat_1")


def create_database():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.database = DB_NAME

        # Create table for schools data
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            school_name VARCHAR(255),
            school_code VARCHAR(100),
            participants INT,
            reussites INT,
            school_option VARCHAR(100),
            province VARCHAR(100),
            years INT,
            PRIMARY KEY schools_unique (school_name, school_option, years, province)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_name VARCHAR(255),
            school_name VARCHAR(255),
            school_option VARCHAR(100),
            province VARCHAR(100),
            student_code VARCHAR(100),
            sexe VARCHAR(100),
            years INT,
            pourcentage INT,
            FOREIGN KEY student_unique (school_name, school_option, years, province) REFERENCES schools(school_name, school_option, years, province) 
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)


        conn.commit()
        print(" Database and tables created successfully!")

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied: check MYSQL_USER and MYSQL_PASSWORD")
        else:
            print(f"MySQL error: {err}")
        raise
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

if __name__ == "__main__":
    create_database()