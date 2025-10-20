import sqlite3
import json
import os
import shutil
from datetime import datetime

def validate_school_data(school):
    """Validate school data for required fields and non-zero values."""
    
    required_fields = ["school_name", "school_code", "school_participants", 
                      "school_reussites", "school_option", "school_province", "year"]
    
    # Check if all required fields exist
    if not all(field in school for field in required_fields):
        return False
    
    # Check for zero or empty values in important fields
    if int(school["school_participants"]) == 0 or int(school["school_reussites"]) == 0:
        return False
        
    return True

def validate_student_data(school_group):
    """Validate student data for required fields and non-empty values."""
    school_required_fields = ["school_name", "option", "year"]
    if not all(field in school_group for field in school_required_fields):
        return False
        
    if not school_group.get("students"):
        return False
    
    # Check individual student fields
    student_required_fields = ["name", "student_code", "sexe", "pourcentage"]
    for student in school_group["students"]:
        if not all(field in student for field in student_required_fields):
            return False
        try:
            if not 0 <= int(student["pourcentage"]) <= 100:
                return False
        except (ValueError, TypeError):
            return False
    
    return True

def ensure_missing_folder():
    """Create missing folder if it doesn't exist."""
    missing_folder = "missing_data"
    if not os.path.exists(missing_folder):
        os.makedirs(missing_folder)
    return missing_folder

def move_to_missing(file_path, reason):
    """Move problematic files to missing folder with timestamp and reason."""
    missing_folder = ensure_missing_folder()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(file_path)
    new_filename = f"{filename}_{timestamp}_{reason}.json"
    new_path = os.path.join(missing_folder, new_filename)
    shutil.copy2(file_path, new_path)
    print(f"Moved problematic file to: {new_path}")

def insert_school_data(json_path, db_name="exetat.db"):
    """Insert school-related JSON data into the schools table."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "schools" not in data or not data["schools"]:
            move_to_missing(json_path, "no_schools_data")
            return False

        valid_schools = 0
        for school in data["schools"]:
            if validate_school_data(school):
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
                valid_schools += 1
        
        if valid_schools == 0:
            move_to_missing(json_path, "no_valid_schools")
            return False

        conn.commit()
        print(f"Inserted {valid_schools} schools from: {os.path.basename(json_path)}")
        return True

    except Exception as e:
        print(f"Error processing {json_path}: {str(e)}")
        move_to_missing(json_path, "error")
        return False
    finally:
        conn.close()

def insert_student_data(json_path, db_name="exetat.db"):
    """Insert student-related JSON data into the students table."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "students_by_school" not in data or not data["students_by_school"]:
            move_to_missing(json_path, "no_students_data")
            return False

        valid_students = 0
        for school_group in data["students_by_school"]:
            if validate_student_data(school_group):
                for student in school_group["students"]:
                    cursor.execute("""
                        INSERT INTO students (school_name, option, year, student_name, student_code, sexe, pourcentage)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        school_group["school_name"],
                        school_group["option"],
                        int(school_group["year"]),
                        student["name"],
                        student["student_code"],
                        student["sexe"],
                        int(student["pourcentage"])
                    ))
                    valid_students += 1

        if valid_students == 0:
            move_to_missing(json_path, "no_valid_students")
            return False

        conn.commit()
        print(f"Inserted {valid_students} students from: {os.path.basename(json_path)}")
        return True

    except Exception as e:
        print(f"Error processing {json_path}: {str(e)}")
        move_to_missing(json_path, "error")
        return False
    finally:
        conn.close()