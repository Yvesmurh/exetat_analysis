import sqlite3

def create_database():
    conn = sqlite3.connect("exetat.db")
    cursor = conn.cursor()

    # Create table for schools data
    cursor.execute("""
CREATE TABLE schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_name TEXT,
    code TEXT,
    participants INTEGER,
    reussites INTEGER,
    option TEXT,
    province TEXT,
    year INTEGER
)
""")

    cursor.execute("""
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER,
    student_name TEXT,
    school_name TEXT,
    option TEXT,
    student_code TEXT,
    sexe TEXT,
    year INTEGER,
    pourcentage INTEGER,
    FOREIGN KEY (school_id, option, year) REFERENCES schools(id, option, year)

)
""")

    conn.commit()
    conn.close()
    print(" Database and tables created successfully!")

