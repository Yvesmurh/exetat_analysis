import json
import sqlite3
import pandas as pd
import pytest

from exetat_dashboard.queries import analytics as q
from exetat_dashboard.queries import helpers
from exetat_dashboard.queries.overview import get_top_students_by_option
from exetat_dashboard.queries.province import get_province_stats
from exetat_dashboard.queries.schools import get_school_choices, get_schools, get_student_ranking
from exetat_dashboard.figures.analytics import build_scope_trend, build_scope_overview, build_option_leaders, build_range_distribution
from exetat_dashboard.utils.analytics_callbacks import next_paging_state, ranking_page
from conftest import call_callback


def test_weighted_rates_and_school_counts(db):
    province = q.get_scope_overview('ALPHA', 2023)
    assert province['total_schools'] == 3  # two option rows are still one school
    assert province['total_participants'] == 200
    assert province['total_successful'] == 60
    assert province['success_rate'] == 30
    assert province['previous_success_rate'] == 85
    assert province['success_rate_delta_vs_prev_year'] == -55
    school = q.get_scope_overview('ALPHA', 2023, school_id=1)
    assert school['total_options'] == 2
    assert school['success_rate'] == 10  # not average(100%,0%) = 50%
    assert school['previous_success_rate'] == 80
    assert q.get_scope_overview('ALPHA', 2023, 'Math', 1)['success_rate'] == 100
    assert q.get_scope_overview('ALPHA', 2023, school_id=3) == {}  # foreign school


def test_missing_and_zero_are_not_fabricated(db):
    assert q.get_scope_overview('ALPHA', 2024) == {}
    assert q.get_scope_overview('ALPHA', 2023, school_id=5) == {}
    assert q.get_scope_overview('ALPHA', 2023, school_id=4)['success_rate'] is None
    commerce = q.get_scope_overview('ALPHA', 2023, 'Commerce', 1)
    assert commerce['success_rate'] == 0
    assert commerce['previous_success_rate'] is None
    assert commerce['success_rate_delta_vs_prev_year'] is None
    assert not get_schools(None, 2023).shape[0]
    assert get_student_ranking('ALPHA', None, 2023).empty


def test_option_leaders_do_not_leak_scope(db):
    province = get_top_students_by_option(2023, province='ALPHA', raise_on_error=True).set_index('option_name')
    school = get_top_students_by_option(2023, province='ALPHA', school_id=1, raise_on_error=True).set_index('option_name')
    assert province.loc['Math', 'top_student_current'] == 'Provincial Leader'
    assert province.loc['Math', 'top_percentage_previous'] == 92
    assert province.loc['Math', 'pts_change'] == 3
    assert school.loc['Math', 'top_student_current'] == 'Alice'
    assert school.loc['Math', 'top_percentage_previous'] == 80
    assert school.loc['Math', 'pts_change'] == 10
    assert pd.isna(school.loc['Commerce', 'top_percentage_previous'])
    assert get_top_students_by_option(2023, 'Commerce', 'ALPHA', 1, raise_on_error=True).shape[0] == 1
    assert get_top_students_by_option(2023, province='ALPHA', school_id=3, raise_on_error=True).empty


def test_school_rank_and_distribution_use_same_weighting(db):
    ranking = get_schools('ALPHA', 2023)
    assert ranking['school_id'].tolist() == [2,1,4]
    assert ranking['success_rate'].iloc[:2].tolist() == [50,10]
    assert pd.isna(ranking['success_rate'].iloc[2])
    bands = q.get_school_rate_distribution('ALPHA', 2023).set_index('bucket_label')['item_count']
    assert bands.sum() == 2  # zero participant school excluded
    assert bands['50–<60%'] == 1 and bands['Below 50%'] == 1


def test_student_ids_boundaries_and_distribution(db):
    ranking = get_student_ranking('ALPHA', 1, 2023)
    assert ranking['student_id'].tolist() == [1,2,10,3]
    assert ranking['student_id'].is_unique
    assert ranking['student_name'].tolist().count('Same Name') == 2
    bands = q.get_school_student_distribution('ALPHA', 1, 2023).set_index('bucket_label')['item_count']
    assert bands.sum() == len(ranking) == 4
    assert bands['90%+'] == bands['80–<90%'] == bands['50–<60%'] == bands['Below 50%'] == 1
    assert get_student_ranking('BETA',1,2023).empty


def test_every_bucket_boundary(db):
    con = sqlite3.connect(db[0])
    for i, score in enumerate([0,49.99,50,59.99,60,69.99,70,79.99,80,89.99,90,100], 100):
        con.execute('INSERT INTO students VALUES (?,?)', (i, f'Boundary {i}'))
        con.execute('INSERT INTO exam_results VALUES (?,?,?,?)', (i,i,5,score))
    con.commit(); con.close()
    distribution = q.get_school_student_distribution('ALPHA',4,2023)
    assert distribution['item_count'].tolist() == [2,2,2,2,2,2]
    figure = build_range_distribution(distribution, school=True)
    assert list(figure.data[0].x) == [2,2,2,2,2,2]


def test_trend_gaps_and_null_denominator(db):
    df = q.get_scope_trend('ALPHA', school_id=1)
    assert df['year'].tolist() == [2015,2017,2021,2022,2023]
    fig = build_scope_trend(df)
    trace = fig.data[0]
    assert list(trace.x) == list(range(2015,2024))
    assert trace.y[0] == 50 and trace.y[1] is None and trace.y[2] == 60
    assert trace.y[6] is None and trace.connectgaps is False


def test_bound_queries_paging_and_safe_search(db):
    choices = get_school_choices('ALPHA', selected_id=3)
    assert 3 not in {c['value'] for c in choices}
    assert get_school_choices('ALPHA', "' OR 1=1 --") == []
    assert get_schools('ALPHA', 2023, "' OR 1=1 --").empty
    get_student_ranking('ALPHA',1,2023,limit=999999,offset=-5)
    assert db[1][-1][1][-2:] == (51,0)
    get_school_choices('ALPHA', 'not found', selected_id=1)
    assert db[1][-1][1] == ('ALPHA','not found','not found','ALPHA',1)


def test_pagination_stability_and_reset(db):
    con = sqlite3.connect(db[0])
    for i in range(100,225):
        con.execute('INSERT INTO students VALUES (?,?)', (i, f'Test Student {i}'))
        con.execute('INSERT INTO exam_results VALUES (?,?,?,?)', (i,i,5,80))
    con.commit(); con.close()
    loader = lambda limit, offset: get_student_ranking('ALPHA',4,2023,limit=limit,offset=offset)
    initial = ranking_page(loader, {}, ['ALPHA',4,2023], None, 'sa', True, school=True)
    assert initial[-1]['has_next'] and db[1][-1][1][-2:] == (11,0)
    expanded = ranking_page(loader, initial[-1], ['ALPHA',4,2023], 'sa-expand', 'sa', True, school=True)
    assert expanded[-1]['expanded'] and db[1][-1][1][-2:] == (51,0)
    next_page = ranking_page(loader, expanded[-1], ['ALPHA',4,2023], 'sa-next', 'sa', True, school=True)
    assert next_page[-1]['page'] == 1 and db[1][-1][1][-2:] == (51,50)
    page1, page2 = loader(50,0), loader(50,50)
    assert set(page1.student_id).isdisjoint(page2.student_id)
    last = ranking_page(loader, next_page[-1], ['ALPHA',4,2023], 'sa-next', 'sa', True, school=True)
    assert not last[-1]['has_next'] and last[5] is True
    reset = next_paging_state(last[-1], ['BETA',4,2023], 'sa-province', 'sa')
    assert reset['page'] == 0 and reset['expanded'] is False


def test_existing_home_option_binding(db):
    get_province_stats(2023, 'Math')
    assert db[1][-1][1] == (2023, 'Math', 2022, 'Math')


def test_errors_do_not_become_zero_statistics(monkeypatch):
    monkeypatch.setattr(helpers, 'get_connection', lambda: (_ for _ in ()).throw(RuntimeError('offline')))
    with pytest.raises(helpers.QueryError):
        q.get_scope_overview('ALPHA',2023)
    assert helpers._read_sql('SELECT 1', default='empty') == 'empty'


def test_routes_ids_and_navigation(app):
    import dash
    from dash.development.base_component import Component
    client = app.server.test_client()
    for route in ['/', '/provinces', '/schools', '/_dash-layout', '/_dash-dependencies', '/assets/style.css']:
        assert client.get(route).status_code == 200
    ids = []
    def walk(node):
        if isinstance(node, (list,tuple)):
            for child in node: walk(child)
        elif isinstance(node, Component):
            if getattr(node,'id',None): ids.append(node.id)
            children = getattr(node,'children',None)
            if isinstance(children, (list, tuple)):
                assert not any(isinstance(child, (list, tuple)) for child in children), type(node).__name__
            walk(children)
    walk(app.layout)
    for page in dash.page_registry.values():
        walk(page['layout']() if callable(page['layout']) else page['layout'])
    assert len(ids) == len(set(ids))
    for entry in app.callback_map.values():
        for field in entry['inputs'] + entry['state']:
            assert field['id'] in ids
    response = call_callback(app, 'nav-provinces', {'app-location.pathname':'/provinces'}, 'app-location.pathname')
    assert response['nav-provinces']['className'] == 'nav-link nav-link--active'
    assert response['nav-overview']['className'] == 'nav-link'


def test_real_dash_callback_requests(app, db):
    inputs = {'pa-province.value':'ALPHA','pa-year.value':2023,'pa-option.value':'Toutes les options'}
    response = call_callback(app, 'pa-overview', inputs, 'pa-province.value')
    text = json.dumps(response)
    assert '30.00%' in text and '95.00%' in text and '100.00%' not in text
    school_inputs = {'sa-province.value':'ALPHA','sa-school.value':1,'sa-year.value':2023,'sa-option.value':'Toutes les options'}
    response = call_callback(app, 'sa-overview', school_inputs, 'sa-school.value')
    text = json.dumps(response)
    assert '10.00%' in text and '90.00%' in text and 'Foreign Leader' not in text
    selector = call_callback(app,'sa-school', {'sa-province.value':'BETA','sa-school.search_value':'School One'},
                             'sa-province.value', {'sa-school.value':1})
    assert selector['sa-school']['value'] == 3
    assert len(selector['sa-school']['options']) == 1
    ranking = call_callback(app,'sa-ranking', school_inputs, 'sa-school.value', {'sa-paging.data':{}})
    assert ranking['sa-paging']['data']['page'] == 0
    assert 'Foreign Leader' not in json.dumps(ranking)


def test_component_failure_is_isolated(app, db, monkeypatch):
    import sys
    page = sys.modules['pages.province']
    monkeypatch.setattr(page, 'get_top_students_by_option', lambda *a, **kw: (_ for _ in ()).throw(helpers.QueryError('offline')))
    response = call_callback(app, 'pa-overview', {'pa-province.value':'ALPHA','pa-year.value':2023}, 'pa-year.value')
    assert '30.00%' in json.dumps(response['pa-overview'])
    assert 'temporarily unavailable' in json.dumps(response['pa-leaders'])
