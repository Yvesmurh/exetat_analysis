"""Isolated SQL fixtures only; never imported or seeded by the application.

SQLite executes the portable SQL subset; sqlglot separately parses each read
in MySQL dialect. This does NOT claim integration with the user's MySQL server.
"""
import re
import sqlite3
import sys
from pathlib import Path

import pytest
import sqlglot

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from exetat_dashboard.queries import helpers

SCHEMA = """
CREATE TABLE pr_after_reform26 (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE educational_province (id INTEGER PRIMARY KEY, name TEXT, province_after_id INTEGER);
CREATE TABLE schools (id INTEGER PRIMARY KEY, school_name TEXT, province_id INTEGER);
CREATE TABLE options (id INTEGER PRIMARY KEY, option_name TEXT);
CREATE TABLE exetat_entry (id INTEGER PRIMARY KEY, school_id INTEGER, years INTEGER, option_id INTEGER,
                           participants INTEGER, reussites INTEGER);
CREATE TABLE students (id INTEGER PRIMARY KEY, student_name TEXT);
CREATE TABLE exam_results (id INTEGER PRIMARY KEY, student_id INTEGER, school_session_id INTEGER, percentage REAL);
"""


class Cursor:
    def __init__(self, raw, statements):
        self.raw, self.statements = raw, statements

    def execute(self, query, params=()):
        assert query.count('%s') == len(params), (query, params)
        sqlglot.parse_one(query.replace('%s', '?'), read='mysql')
        self.statements.append((query, tuple(params)))
        self.raw.execute(query.replace('%s', '?'), params)
        return self

    def __getattr__(self, name):
        return getattr(self.raw, name)


class Connection:
    def __init__(self, path, statements):
        self.raw, self.statements = sqlite3.connect(path), statements
        self.raw.create_function('LOCATE', 2, lambda needle, value: (value or '').find(needle) + 1)
        self.raw.create_function('REGEXP', 2, lambda pattern, value: bool(re.search(pattern, value or '')))

    def cursor(self):
        return Cursor(self.raw.cursor(), self.statements)

    def __getattr__(self, name):
        return getattr(self.raw, name)


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / 'isolated_tests.db'
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany('INSERT INTO pr_after_reform26 VALUES (?,?)', [(1, 'ALPHA'), (2, 'BETA')])
    con.executemany('INSERT INTO educational_province VALUES (?,?,?)', [(10, 'A1', 1), (11, 'A2', 1), (20, 'B1', 2)])
    con.executemany('INSERT INTO schools VALUES (?,?,?)', [(1, 'School One', 10), (2, 'School Two', 11),
                       (3, 'Foreign School', 20), (4, 'Zero Participants', 10), (5, 'No Results', 10)])
    con.executemany('INSERT INTO options VALUES (?,?)', [(1, 'Math'), (2, 'Commerce')])
    con.executemany('INSERT INTO exetat_entry VALUES (?,?,?,?,?,?)', [
        (1,1,2023,1,10,10), (2,1,2023,2,90,0), (3,2,2023,1,100,50),
        (4,3,2023,1,100,100), (5,4,2023,1,0,0),
        (6,1,2022,1,10,8), (7,2,2022,1,10,9), (8,3,2022,1,100,100),
        (9,1,2015,1,10,5), (10,1,2017,1,20,12), (11,1,2021,1,0,0),
    ])
    # IDs, not names, determine student identity; include same-name people.
    con.executemany('INSERT INTO students VALUES (?,?)', [(1,'Alice'), (2,'Same Name'), (3,'Same Name'),
                       (4,'Provincial Leader'), (5,'Foreign Leader'), (6,'Prior One'),
                       (7,'Prior Province'), (8,'Prior Foreign'), (9,'Unknown'), (10,'Boundary')])
    con.executemany('INSERT INTO exam_results VALUES (?,?,?,?)', [
        (1,1,1,90), (2,2,1,89.99), (3,3,2,49.9), (4,4,3,95), (5,5,4,100),
        (6,6,6,80), (7,7,7,92), (8,8,8,100),
        (9,1,1,90),  # duplicate result row must not duplicate the student
        (10,1,2,85), # repeated student across options: best result retained
        (11,9,1,None), (12,9,1,110), (13,10,2,50),
    ])
    con.commit(); con.close()
    statements = []
    monkeypatch.setattr(helpers, 'get_connection', lambda: Connection(path, statements))
    return path, statements


@pytest.fixture(scope='session')
def app():
    from exetat_dashboard.app import app
    app.server.test_client().get('/_dash-layout')
    return app


def call_callback(app, target, values, changed, states=None):
    key = next(key for key, entry in app.callback_map.items()
               if any(out.component_id == target for out in
                      (entry['output'] if isinstance(entry['output'], list) else [entry['output']])))
    entry = app.callback_map[key]
    outputs = entry['output']
    output_json = lambda item: {'id': item.component_id, 'property': item.component_property}
    payload = {
        'output': key,
        'outputs': [output_json(item) for item in outputs] if isinstance(outputs, list) else output_json(outputs),
        'inputs': [dict(item, value=values.get(f"{item['id']}.{item['property']}")) for item in entry['inputs']],
        'state': [dict(item, value=(states or {}).get(f"{item['id']}.{item['property']}")) for item in entry['state']],
        'changedPropIds': [changed],
    }
    response = app.server.test_client().post('/_dash-update-component', json=payload)
    assert response.status_code == 200, response.get_data(as_text=True)
    return response.get_json()['response']
