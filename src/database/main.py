import os
import json
import argparse
import logging
from create_db import create_database

from db import get_connection
from insert import (
    extract_schools,
    insert_provinces,
    insert_options,
    insert_schools,
    insert_exetat_entries,
    build_exetat_map,
    insert_students,
)

logging.basicConfig(level=logging.INFO)
DATA_DIR= "/home/yves-s-computer/Exetat_analysis/json_files/2009"

def discover_files(data_dir):
    """
    Discover and categorize JSON files in the given directory.

    Scans the directory for files ending with '_schools_data.json' and '_students_data.json',
    grouping them by a common key (derived from the filename before the suffix).

    Args:
        data_dir (str): The path to the directory containing the JSON files.

    Returns:
        tuple: A tuple containing two dictionaries:
            - schools_files: dict with key as filename prefix and value as full path to schools file.
            - students_files: dict with key as filename prefix and value as full path to students file.
    """
    # Initialize dictionaries to hold file paths
    schools_files = {}
    students_files = {}

    # Iterate over all files in the directory
    for file in os.listdir(data_dir):
        path = os.path.join(data_dir, file)

        # Check if it's a schools data file
        if file.endswith("_schools_data.json"):
            key = file.replace("_schools_data.json", "")
            schools_files[key] = path

        # Check if it's a students data file
        elif file.endswith("_students_data.json"):
            key = file.replace("_students_data.json", "")
            students_files[key] = path

    return schools_files, students_files


def match_pairs(schools_files, students_files):
    """
    Match schools and students files into pairs based on common keys.

    For each key in schools_files, if there's a corresponding key in students_files,
    create a pair (schools_path, students_path). Log warnings for unmatched files.

    Args:
        schools_files (dict): Dictionary of schools files.
        students_files (dict): Dictionary of students files.

    Returns:
        list: List of tuples, each containing (schools_file_path, students_file_path).
    """
    pairs = []

    # Match schools files with corresponding students files
    for key in schools_files:
        if key in students_files:
            pairs.append((schools_files[key], students_files[key]))
        else:
            logging.warning(f"No student file for {key}")

    # Check for unmatched students files
    for key in students_files:
        if key not in schools_files:
            logging.warning(f"No school file for {key}")

    return pairs


def main():
    """
    Main entry point for the data pipeline.

    Processes JSON files from the specified directory, extracts data, inserts into database,
    and commits changes. Handles errors by rolling back transactions.

    The pipeline steps:
    1. Discover and pair schools and students JSON files.
    2. For each pair, load data, extract entities.
    3. Insert provinces, options, schools, exetat entries.
    4. Build exetat map and insert students with exam results.
    5. Commit or rollback on error.

    Raises:
        ValueError: If the data directory is invalid or no file pairs are found.
        Exception: Any exception during processing, after rollback.
    """

    # Uncomment to create database tables if needed
    create_database()

    data_dir = DATA_DIR

    # Validate data directory
    if not os.path.isdir(data_dir):
        raise ValueError(f"Invalid directory: {data_dir}")

    # Establish database connection
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Discover and pair JSON files
        schools_files, students_files = discover_files(data_dir)
        pairs = match_pairs(schools_files, students_files)

        if not pairs:
            raise ValueError("No valid file pairs found")

        # Process each pair of files. If one file is malformed or processing fails
        # for that pair, log the offending files, rollback that transaction and
        # continue with the remaining pairs.
        failed_pairs = []
        for schools_path, students_path in sorted(pairs):
            logging.info(f"Processing: {schools_path} + {students_path}")
            try:
                # Load schools data
                with open(schools_path, encoding="utf-8") as f:
                    schools_data = json.load(f)

                # Load students data
                with open(students_path, encoding="utf-8") as f:
                    students_data = json.load(f)

                # Extract data from schools JSON
                province_set, option_set, school_dict, exetat_list = \
                    extract_schools(schools_data.get("schools", []))

                # Insert data into database
                province_map = insert_provinces(cursor, province_set)
                option_map   = insert_options(cursor, option_set)
                school_map   = insert_schools(cursor, school_dict, province_map)
                insert_exetat_entries(cursor, exetat_list, school_map, option_map)

                # Build map for students insertion
                exetat_map = build_exetat_map(cursor)
                insert_students(cursor, students_data.get("students_by_school", []), exetat_map)

                # Commit transaction for this pair
                conn.commit()

            except json.JSONDecodeError as e:
                # Malformed JSON — rollback this pair and continue
                conn.rollback()
                logging.error(f"JSON decode error in {schools_path} or {students_path}: {e}")
                failed_pairs.append((schools_path, students_path, str(e)))
                continue

            except Exception as e:
                # Any other processing error — rollback this pair and continue
                conn.rollback()
                logging.error(f"Failed processing {schools_path} + {students_path}: {e}")
                failed_pairs.append((schools_path, students_path, str(e)))
                continue

        if failed_pairs:
            logging.warning("Some file pairs failed to process:")
            for a, b, reason in failed_pairs:
                logging.warning(f"  {a} + {b}: {reason}")

        logging.info("All files processed successfully.")

    except Exception as e:
        # Rollback on error
        conn.rollback()
        logging.error(f"Pipeline failed: {e}")
        raise

    finally:
        # Clean up database resources
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()