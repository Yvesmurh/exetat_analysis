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

        #the provinces are inserted in the db manualy . they aren't inserted with the insertion module 
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pr_before_reform11 (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE
            )ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        #the provinces too are inserted in the db manualy . they aren't inserted with the insertion module 
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pr_after_reform26 (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE
            )ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS educational_province (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                province_before_id INT,
                province_after_id INT, 
                FOREIGN KEY (province_before_id) REFERENCES pr_before_reform11(id),
                FOREIGN KEY (province_after_id) REFERENCES pr_after_reform26(id)
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
                INDEX school_name (school_name),
                INDEX idx_province (province_id),
                FOREIGN KEY (province_id) REFERENCES educational_province(id)
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
                INDEX idx_years (years),
                INDEX idx_years_option (years, option_id),
                INDEX idx_years_school (years, school_id),
                INDEX option_id (option_id),
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
                student_code VARCHAR(100) NOT NULL,
                student_name VARCHAR(255) NOT NULL,
                sexe VARCHAR(16),
                INDEX student_name (student_name)
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
                UNIQUE KEY idx_student_session (student_id, school_session_id),
                INDEX idx_percentage_session (percentage, school_session_id),
                INDEX school_session_id (school_session_id),
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