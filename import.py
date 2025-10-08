import json
import sqlite3

# 1. Connect to database
conn = sqlite3.connect("exetat.db")
cursor = conn.cursor()

cursor.executescript("""
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
    FOREIGN KEY (school_id) REFERENCES schools(id)
);
""")

# 3. Load data from your JSON files
with open("json_files/Palmares_PROVINCE-ORIENTALE-4-54_2015_schools_data.json", "r", encoding="utf-8") as f:
    schools_data = json.load(f)

with open("json_files/Palmares_PROVINCE-ORIENTALE-4-54_2015_students_data.json", "r", encoding="utf-8") as f:
    students_data = json.load(f)

# 4. Insert data into 'schools' table
for school in schools_data["schools"]:
    cursor.execute("""
        INSERT INTO schools (school_name, code, participants, reussites, option, province, year)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        school["school_name"],
        school["school_code"],
        int(school["school_participants"]),
        int(school["school_reussites"]),
        school["school_option"],
        school["school_province"],
        int(school["year"])
    ))

# 5. Insert data into 'students' table
for school_group in students_data["students_by_school"]:
    for student in school_group["students"]:
        cursor.execute("""
            INSERT INTO students (school_name, option, year, student_name, student_code, sexe, pourcentage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            school_group["school_name"],
            school_group["option"],
            int(school["year"]),
            student["name"],
            student["student_code"],
            student["sexe"],
            int(student["pourcentage"])
        ))

# 6. Commit changes and close connection
conn.commit()
conn.close()

print("✅ Data successfully imported into the database!")
