"""Validate the analytics queries against the user's existing MySQL connection.

Run from the parent directory:
    python -m exetat_dashboard.tools.validate_analytics
No schema changes, data writes, or participant/student data dumps are performed.
"""
import argparse
import sys
from exetat_dashboard.queries.helpers import get_connection

# Required columns are taken only from the original project's SQL relationships.
REQUIRED_COLUMNS = {
    'schools': {'id', 'school_name', 'province_id'},
    'students': {'id', 'student_name'},
    'options': {'id', 'option_name'},
    'exetat_entry': {'id', 'school_id', 'years', 'option_id', 'participants', 'reussites'},
    'exam_results': {'student_id', 'school_session_id', 'percentage'},
    'educational_province': {'id', 'province_after_id'},
    'pr_after_reform26': {'id', 'name'},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--province', help='Exact pr_after_reform26.name value; defaults to first available')
    parser.add_argument('--year', type=int, help='Defaults to latest available year')
    parser.add_argument('--school-id', type=int, help='Defaults to first school in the selected province')
    parser.add_argument('--option', default='Toutes les options')
    args = parser.parse_args()
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute('''SELECT TABLE_NAME, COLUMN_NAME
                                  FROM information_schema.COLUMNS
                                  WHERE TABLE_SCHEMA = DATABASE()''')
                actual = {}
                for table, column in cursor.fetchall():
                    actual.setdefault(table, set()).add(column)
                missing = {table: sorted(cols - actual.get(table, set()))
                           for table, cols in REQUIRED_COLUMNS.items() if cols - actual.get(table, set())}
                if missing:
                    print('FAIL: Required columns missing:', missing)
                    return 1
                print('PASS: Required tables and columns are present.')
                cursor.execute('''SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                                  FROM information_schema.KEY_COLUMN_USAGE
                                  WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL''')
                relationships = cursor.fetchall()
                relevant = [row for row in relationships if row[0] in REQUIRED_COLUMNS]
                print(f'INFO: {len(relevant)} declared foreign-key relationships found for these tables.')
                for table, column, target, key in relevant:
                    print(f'  {table}.{column} -> {target}.{key}')
                cursor.execute('SELECT name FROM pr_after_reform26 ORDER BY name LIMIT 1')
                first = cursor.fetchone()
                province = args.province or (first[0] if first else None)
                cursor.execute('SELECT MAX(years) FROM exetat_entry')
                latest = cursor.fetchone()
                year = args.year if args.year is not None else (latest[0] if latest else None)
            finally:
                cursor.close()
        finally:
            conn.close()
        if not province or year is None:
            print('INFO: Schema checked, but no province/year data is available to exercise queries.')
            return 0
        from exetat_dashboard.queries.analytics import (
            get_scope_overview, get_scope_trend, get_school_rate_distribution, get_school_student_distribution,
        )
        from exetat_dashboard.queries.overview import get_top_students_by_option
        from exetat_dashboard.queries.schools import get_school_choices, get_schools, get_student_ranking
        choices = get_school_choices(province, selected_id=args.school_id)
        school_id = args.school_id if args.school_id is not None else (choices[0]['value'] if choices else None)
        operations = [
            ('Province overview', lambda: get_scope_overview(province, year, args.option)),
            ('Province option leaders', lambda: get_top_students_by_option(year, args.option, province, raise_on_error=True)),
            ('Province trend', lambda: get_scope_trend(province, args.option)),
            ('School ranking preview', lambda: get_schools(province, year, args.option, limit=11)),
            ('School success-rate distribution', lambda: get_school_rate_distribution(province, year, args.option)),
        ]
        if school_id is not None:
            operations.extend([
                ('School overview', lambda: get_scope_overview(province, year, args.option, school_id)),
                ('School option leaders', lambda: get_top_students_by_option(year, args.option, province, school_id, raise_on_error=True)),
                ('School trend', lambda: get_scope_trend(province, args.option, school_id)),
                ('Student ranking preview', lambda: get_student_ranking(province, school_id, year, args.option, limit=11)),
                ('Student distribution', lambda: get_school_student_distribution(province, school_id, year, args.option)),
            ])
        failures = 0
        for label, operation in operations:
            try:
                result = operation()
                print(f'PASS: {label} (empty selection)' if len(result) == 0 else f'PASS: {label}')
            except Exception as exc:
                failures += 1
                print(f'FAIL: {label} ({type(exc.__cause__ or exc).__name__}); inspect the chained error locally.')
        return int(failures > 0)
    except Exception as exc:
        print(f'FAIL: Could not validate the database ({type(exc).__name__}).')
        print('Ensure the existing database/db.py package, its driver and connection configuration are available.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
