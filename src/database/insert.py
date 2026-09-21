import argparse
import json
import logging
import sys
from typing import Dict, List, Tuple

import mysql.connector
from mysql.connector import Error
from db import get_connection

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


BATCH_SIZE = 1000



def chunked(iterable, size):
    """
    Split an iterable into chunks of a specified size.

    Yields successive chunks from the iterable, each of the given size,

    
    it takes the The iteration to be chunked. and the size (int): The size of each chunk.

    and then return list: A chunk of the iterable.but those chunks are process at a time 
    that why we're using yeild instead of return 
    """
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


def extract_province(records: list) -> set:
    province_set = set()
    for r in records:
        try:
            province_set.add(r["school_province"])
        except KeyError:
            pass
    return province_set


def extract_options(records: list) -> set:
    option_set = set()
    for r in records:
        try:
            option_set.add(r["school_option"])
        except KeyError:
            pass
    return option_set


def extract_schools_dict(records: list) -> dict:
    school_dict = {}
    for r in records:
        try:
            code = r["school_code"]
            if code not in school_dict:
                school_dict[code] = (r["school_name"], r["school_province"])
        except KeyError:
            pass
    return school_dict


def extract_exetat_list(records: list) -> list:
    exetat_list = []
    for r in records:
        try:
            exetat_list.append({
                "school_code": r["school_code"],
                "option_name": r["school_option"],
                "year": int(r["year"]),
                "participants": int(r["school_participants"]),
                "reussites": int(r["school_reussites"]),
            })
        except KeyError as e:
            logging.warning(f"Missing field {e} in school record – skipped")
    return exetat_list


def extract_schools(records: list):
    """
    Extract educational_provinces, options, schools, and exetat entries from schools records.

    Processes a list of school records, collecting unique provinces and options,
    building a school dictionary, and creating exetat entry data.

    
    it takes records (list): List of dictionaries representing school records.

    Returns:
        tuple: (province_set, option_set, school_dict, exetat_list)
            - province_set (set): Unique province names.
            - option_set (set): Unique option names.
            - school_dict (dict): {school_code: (school_name, province_name)}
            - exetat_list (list): List of exetat entry dictionaries.
    """
    province_set = extract_province(records)
    option_set = extract_options(records)
    school_dict = extract_schools_dict(records)
    exetat_list = extract_exetat_list(records)
    # a ka swall useful code to help track the processing staff .. and keep tracking of data processed 
    logging.info(
        f"Extracted: {len(province_set)} province(s), {len(option_set)} option(s), "
        f"{len(school_dict)} school(s), {len(exetat_list)} exetat entry row(s)"
    )
    return province_set, option_set, school_dict, exetat_list



def insert_and_map(cursor, table: str, column: str, values: set) -> Dict[str, int]:
    """
    Insert unique values into a table and return a mapping of value to ID.

    Performs INSERT IGNORE on the set of values, then queries the table to build
    a dictionary mapping each value to its ID.

    it takes as Arguments:
        cursor: Database cursor.
        table (str): Table name.
        column (str): Column name for the values.
        values (set): Set of unique values to insert.

    and Returns:
        Dict[str, int]: Mapping of value to ID.
    """
    if values:
        # Bulk insert unique values
        cursor.executemany(
            f"INSERT IGNORE INTO {table} ({column}) VALUES (%s)",
            [(v,) for v in values]
        )
        logging.info(f"  {table}: {cursor.rowcount} new row(s) inserted")
    # Fetch the mapping
    cursor.execute(f"SELECT id, {column} FROM {table}")
    return {name: _id for _id, name in cursor.fetchall()}



def insert_provinces(cursor, province_set: set) -> Dict[str, int]:
    """
    Insert unique province names and return a mapping.

    Args:
        cursor: Database cursor.
        province_set (set): Set of province names.

    Returns:
        Dict[str, int]: Mapping of province name to ID.
    """
    return insert_and_map(cursor, "educational_provinces", "name", province_set)



def insert_options(cursor, option_set: set) -> Dict[str, int]:
    """
    Insert unique option names and return a mapping.

    Args:
        cursor: Database cursor.
        option_set (set): Set of option names.

    Returns:
        Dict[str, int]: Mapping of option name to ID.
    """
    return insert_and_map(cursor, "options", "option_name", option_set)



def insert_schools(cursor, school_dict: dict, province_map: Dict[str, int]) -> Dict[str, int]:
    """
    Insert schools into the database and return a mapping.

    Resolves province IDs from the province_map and bulk inserts schools.

    Args:
        cursor: Database cursor.
        school_dict (dict): {school_code: (school_name, province_name)}
        province_map (Dict[str, int]): Mapping of province name to ID.

    Returns:
        Dict[str, int]: Mapping of school_code to school ID.
    """
    #question ...........
    #here rows in list is important because with it we can have a list of code, name, pro_id and 
    #with it when executing executemay it will send many row at once 
    rows = []
    for code, (name, province) in school_dict.items():
        pro_id = province_map.get(province)
        if pro_id is not None:
            rows.append((code, name, pro_id))
        else:
            logging.warning(f"Province not found: {province!r} – school {code} skipped")

    # Bulk insert schools: a bulk operation is performing the same operation on many piece of data at once 
    for batch in chunked(rows, BATCH_SIZE):
        #don't silence your error so leave that insert ignore
        #it look like here i might need to use the constraint ON DUPLICATED KEY 
        cursor.executemany(
            "INSERT INTO schools (school_code, school_name, province_id) VALUES (%s, %s, %s)",
            batch
        )
    logging.info(f"  schools: {len(rows)} row(s) processed")

    # Fetch school mapping
    cursor.execute("SELECT id, school_code FROM schools")
    return {code: sid for sid, code in cursor.fetchall()}



def insert_exetat_entries(cursor, exetat_list: list, school_map: dict, option_map: dict) -> None:
    """
    Insert exetat entries into the database.

    Resolves school and option IDs, then bulk inserts with ON DUPLICATE KEY UPDATE.

    Args:
        cursor: Database cursor.
        exetat_list (list): List of exetat entry dictionaries.
        school_map (dict): Mapping of school_code to school ID.
        option_map (dict): Mapping of option_name to option ID.
    """
    rows    = []
    skipped = 0

    for e in exetat_list:
        sid = school_map.get(e["school_code"])
        oid = option_map.get(e["option_name"])

        if sid and oid:
            rows.append((sid, e["year"], oid, e["participants"], e["reussites"]))
        else:
            logging.warning(f"Missing school/option mapping for {e['school_code']} – skipped")
            skipped += 1

    # need to be change at the point of duplication key 
    for batch in chunked(rows, BATCH_SIZE):
        cursor.executemany(
            """
            INSERT INTO exetat_entry (school_id, years, option_id, participants, reussites)
            VALUES (%s, %s, %s, %s, %s)
            """,
            batch
        )
    logging.info(f"  exetat_entry: {len(rows)} processed, {skipped} skipped")


def build_exetat_map(cursor) -> dict:
    """
    Build a mapping from (school_code, option_name, year) to exetat_entry ID.

    Queries the database to create a lookup map for exetat entries.

    Args:
        cursor: Database cursor.

    Returns:
        dict: {(school_code, option_name, year): exetat_entry_id}
    """
    # Query to get exetat entries with joined school and option names
    cursor.execute(
        """
        SELECT ee.id, s.school_code, o.option_name, ee.years
          FROM exetat_entry ee
          JOIN schools s ON ee.school_id = s.id
          JOIN options o ON ee.option_id  = o.id
        """
    )
    return {
        (code, opt, year): eid
        for eid, code, opt, year in cursor.fetchall()
    }

def extract_student_data(groups: list, exetat_map: dict) -> Tuple[List, List, int]:
    student_rows = []
    result_rows = []
    skipped = 0
    for g in groups:
        code = g.get("school_code")
        option = g.get("option")
        year = int(g.get("year", 0))
        ex_id = exetat_map.get((code, option, year))
        if not ex_id:
            logging.warning(
                f"No exetat_entry for ({code!r}, {option!r}, {year}) "
                f"– {len(g.get('students', []))} student(s) skipped"
            )
            skipped += len(g.get("students", []))
            continue
        for s in g.get("students", []):
            try:
                student_rows.append((s["student_code"], s["name"], s.get("sexe")))
                result_rows.append((s["student_code"], ex_id, float(s["pourcentage"])))
            except KeyError as e:
                logging.warning(f"Missing field {e} in student record – skipped")
                skipped += 1
    return student_rows, result_rows, skipped


def insert_students_bulk(cursor, student_rows: List) -> None:
    if not student_rows:
        return
    for batch in chunked(student_rows, BATCH_SIZE):
        cursor.executemany(
            "INSERT INTO students (student_code, student_name, sexe) VALUES (%s, %s, %s)",
            batch
        )
    logging.info(f"  students: {cursor.rowcount} new row(s) inserted (last batch)")


def build_student_map(cursor, codes: List) -> Dict[str, int]:
    student_map = {}
    for batch in chunked(codes, BATCH_SIZE):
        fmt = ",".join(["%s"] * len(batch))
        cursor.execute(
            f"SELECT id, student_code FROM students WHERE student_code IN ({fmt})",
            batch
        )
        student_map.update({code: sid for sid, code in cursor.fetchall()})
    return student_map


def insert_exam_results_bulk(cursor, result_rows: List, student_map: Dict[str, int]) -> int:
    final_rows = []
    skipped = 0
    for code, ex_id, pct in result_rows:
        sid = student_map.get(code)
        if sid:
            final_rows.append((sid, ex_id, pct))
        else:
            logging.warning(f"student_code {code!r} not resolved – exam result skipped")
            skipped += 1
    for batch in chunked(final_rows, BATCH_SIZE):
        cursor.executemany(
            """
            INSERT INTO exam_results (student_id, school_session_id, percentage)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE percentage = VALUES(percentage)
            """,
            batch
        )
    logging.info(f"  exam_results: {len(final_rows)} processed, {skipped} skipped")
    return skipped


def insert_students(cursor, groups: list, exetat_map: dict) -> None:
    """
    Insert students and their exam results into the database.

    Processes groups of students by school, resolves exetat IDs, inserts students
    and exam results in batches.

    Args:
        cursor: Database cursor.
        groups (list): List of student groups from JSON.
        exetat_map (dict): Mapping from (school_code, option, year) to exetat_id.
    """
    student_rows, result_rows, skipped = extract_student_data(groups, exetat_map)
    if not student_rows:
        logging.info("  No students to insert.")
        return
    insert_students_bulk(cursor, student_rows)
    codes = list({r[0] for r in student_rows})
    student_map = build_student_map(cursor, codes)
    insert_exam_results_bulk(cursor, result_rows, student_map)