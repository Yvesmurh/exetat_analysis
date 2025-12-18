import os
from create_db import create_database
from insert import insert_school_data, insert_student_data
from month import december
december(status_vue)
finissons c

def main():
    # 1. Create database and tables
    # create_database()

    # 2. Define JSON directories
    path = os.path.join(os.path.dirname(__file__), "..", "..", "json_files", "2017")
    if not os.path.exists(path):
        print(f"Error: Directory '{path}' not found")
        return


    print("\nInserting school JSON data...")
    school_files = [f for f in os.listdir(path) if f.endswith("schools_data.json")]
    total_files = len(school_files)
    processed_files = 0
    
    for file in school_files:
        try:
            success = insert_school_data(os.path.join(path, file))
            processed_files += 1
            print(f"Progress: {processed_files}/{total_files} files processed")
            if not success:
                print(f"Failed to process school data from {file}")
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")
            processed_files += 1
            print(f"Progress: {processed_files}/{total_files} files processed")

    # 4. Insert student data
    print("\nInserting student JSON data...")
    student_files = [f for f in os.listdir(path) if f.endswith("students_data.json")]
    total_files = len(student_files)
    processed_files = 0
    
    for file in student_files:
        try:
            success = insert_student_data(os.path.join(path, file))
            processed_files += 1
            print(f"Progress: {processed_files}/{total_files} files processed")
            if not success:
                print(f"Failed to process student data from {file}")
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")
            processed_files += 1


if __name__ == "__main__":
    main()
