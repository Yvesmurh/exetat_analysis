import os
import sys
from db import get_connection
import mysql.connector
from mysql.connector import errorcode

def create_database():
    """
    Create the database tables if they do not already exist.

    This function establishes a connection to the MySQL database and executes
    CREATE TABLE statements for all required tables: provinces, options, schools,
    exetat_entry, students, and exam_results. It uses 'IF NOT EXISTS' to avoid
    errors if tables already exist. Commits the changes upon success.

    Raises:
        mysql.connector.Error: If there's an issue with database access or SQL execution.
    """
    conn = None
    cursor = None

    try:
        # Establish database connection
        conn = get_connection()
        cursor = conn.cursor()

        # Create provinces table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS provinces (
                id INT AUTO_INCREMENT PRIMARY KEY,
                province_name VARCHAR(255) NOT NULL UNIQUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Create options table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS options (
                id INT AUTO_INCREMENT PRIMARY KEY,
                option_name VARCHAR(255) NOT NULL UNIQUE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Create schools table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schools (
                id INT AUTO_INCREMENT PRIMARY KEY,
                school_code VARCHAR(100) NOT NULL,
                school_name VARCHAR(255) NOT NULL,
                province_id INT NOT NULL,
                INDEX (school_name),
                FOREIGN KEY (province_id) REFERENCES provinces(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Create exetat_entry table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exetat_entry (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                school_id INT NOT NULL,
                years INT NOT NULL,
                option_id INT NOT NULL,
                participants INT NOT NULL DEFAULT 0,
                reussites INT NOT NULL DEFAULT 0,
                UNIQUE KEY idx_school_year_option (school_id, years, option_id),
                FOREIGN KEY (school_id) REFERENCES schools(id),
                FOREIGN KEY (option_id) REFERENCES options(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Create students table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                student_code VARCHAR(100) NOT NULL UNIQUE,
                student_name VARCHAR(255) NOT NULL,
                sexe VARCHAR(16),
                INDEX (student_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Create exam_results table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exam_results (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                student_id BIGINT NOT NULL,
                school_session_id BIGINT NOT NULL,
                percentage DECIMAL(5,2) NOT NULL,
                INDEX (percentage),
                UNIQUE KEY idx_student_session (student_id, school_session_id),
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (school_session_id) REFERENCES exetat_entry(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        # Commit all table creations
        conn.commit()
        print("Database and tables created successfully!")

    except mysql.connector.Error as err:
        # Handle specific MySQL errors
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied: check MYSQL_USER and MYSQL_PASSWORD")
        else:
            print(f"MySQL error: {err}")
        raise
    finally:
        # Clean up resources
        for resource in (cursor, conn,):
            if resource is not None:
                try:
                    resource.close()
                except Exception:
                    pass

if __name__ == "__main__":
    create_database()