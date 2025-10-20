from typing import Any

CREATE_TABLE_STATEMENT = """
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS schools;

CREATE TABLE schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_name TEXT,
    code TEXT,
    participants INTEGER,
    reussites INTEGER,
    option TEXT,
    province TEXT,
    year INTEGER
);

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

);
"""
def create_table ( connection):

    cursor = connection.cursor()
    cursor.executescript(CREATE_TABLE_STATEMENT)
    connection.commit()
    connection.close()


    


