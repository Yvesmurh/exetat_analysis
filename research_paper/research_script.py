
"""Search OpenAlex for EXETAT-related literature. Python 3.10+, no dependencies.

Run: python education_literature_search.py --output education_review
Optional: set OPENALEX_API_KEY in your environment (never saved in outputs).
Resume: repeat the same command. New strategy/date range: use a new output folder.
Search scope: titles and abstracts only (missing abstracts reduce recall).
Default period: 2000-01-01 through today. No language/type/OA restriction.
Outputs: results.json, results.csv, checkpoint.json (queries, dates, page audit).
Metadata and available abstracts/links only; does not download full-text papers.
Candidate records require manual relevance, publication-type and quality screening.
Search matching is not proof of study location. No claim of exhaustive coverage.
Do not run simultaneous instances in the same output folder.
Docs: https://help.openalex.org/api/searching/
      https://help.openalex.org/api/authentication/
      https://help.openalex.org/api/paging/
"""
import argparse
import csv
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Two complementary literature streams: dashboard use, and data transparency.
# Matching either stream is intentional; not every useful paper covers both.
EDUCATION = '("learning analytics" OR "educational dashboard" OR "education dashboard" OR "academic dashboard" OR "student performance" OR "school performance" OR "educational data" OR "examination results" OR "higher education" OR "student learning" OR "school management")'
DASHBOARD = '(dashboard OR dashboards OR "learning analytics dashboard" OR "academic dashboard")'
EDUCATION_DATA = '("educational data" OR "education data" OR "school data" OR "student performance data" OR "examination results" OR "school performance" OR "education management information system" OR "school report card" OR "school report cards")'
TRANSPARENCY = '(transparency OR accountability OR "public reporting" OR "public access" OR "information disclosure" OR "open data")'
QUERIES = {
    'educational_dashboards': f'{EDUCATION} AND {DASHBOARD}',
    'educational_data_transparency': f'{EDUCATION_DATA} AND {TRANSPARENCY}',
    'french_educational_dashboards': '("tableau de bord" OR "tableaux de bord") AND (éducation OR scolaire OR scolaires OR étudiant OR étudiants OR université OR apprentissage)',
    'french_educational_data_transparency': '("données éducatives" OR "données scolaires" OR "résultats scolaires" OR "résultats des examens") AND (transparence OR redevabilité OR responsabilisation OR "données ouvertes" OR "accès public")',
}
SEARCH_FIELD = 'title_and_abstract.search'



def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)


def request_page(params):
    headers = {'User-Agent': 'EXETAT-literature-review/1.0'}
    if os.environ.get('OPENALEX_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['OPENALEX_API_KEY']
    req = Request('https://api.openalex.org/works?' + urlencode(params), headers=headers)
    for attempt in range(5):
        try:
            with urlopen(req, timeout=60) as response:
                data = json.load(response)
            if not isinstance(data.get('results'), list) or 'meta' not in data:
                raise RuntimeError('Unexpected API response; page was not saved.')
            return data
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f'OpenAlex HTTP {exc.code}. Check API access and query syntax.') from None
            if attempt == 4:
                raise RuntimeError(f'OpenAlex HTTP {exc.code}. Retry later; progress retained.') from None
            wait = exc.headers.get('Retry-After', '')
            if wait.isdigit() and int(wait) > 60:
                raise RuntimeError('API requests a longer pause; rerun later to resume.') from None
            time.sleep(max(2 ** (attempt + 1), int(wait) if wait.isdigit() else 0))
        except (URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            if attempt == 4:
                raise RuntimeError('Network or response failure; rerun to resume.') from None
            time.sleep(2 ** (attempt + 1))


def abstract_text(index):
    if not index:
        return ''
    positions = [(position, word) for word, offsets in index.items() for position in offsets]
    return ' '.join(word for _, word in sorted(positions))


def parse_work(work):
    location = work.get('primary_location') or {}
    source = location.get('source') or {}
    oa = work.get('open_access') or {}
    best = work.get('best_oa_location') or {}
    return {
        'openalex_id': work['id'], 'doi': work.get('doi'),
        'title': work.get('display_name'), 'year': work.get('publication_year'),
        'publication_date': work.get('publication_date'), 'type': work.get('type'),
        'language': work.get('language'),
        'authors': [a['author'].get('display_name', '') for a in work.get('authorships', [])],
        'source': source.get('display_name'),
        'abstract': abstract_text(work.get('abstract_inverted_index')),
        'is_oa': oa.get('is_oa'), 'oa_url': oa.get('oa_url'),
        'pdf_url': best.get('pdf_url'), 'landing_page_url': location.get('landing_page_url'),
        'cited_by_count': work.get('cited_by_count'), 'is_retracted': work.get('is_retracted'),
        'matched_queries': [], 'openalex_ids': [work['id']],
    }


def merge_works(records, works, label):
    by_id = {i: r for r in records for i in r['openalex_ids']}
    by_doi = {r['doi'].lower().rstrip('/'): r for r in records if r.get('doi')}
    for work in works:
        doi = (work.get('doi') or '').lower().rstrip('/')
        record = by_id.get(work['id']) or (by_doi.get(doi) if doi else None)
        if record is None:
            record = parse_work(work)
            records.append(record)
        if work['id'] not in record['openalex_ids']:
            record['openalex_ids'].append(work['id'])
        if label not in record['matched_queries']:
            record['matched_queries'].append(label)
        by_id[work['id']] = record
        if doi:
            by_doi[doi] = record


def export(folder, state):
    records = state['records']
    atomic_json(folder / 'results.json', records)
    fields = list(parse_work({'id': ''}))
    temporary = folder / 'results.csv.tmp'
    with temporary.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for record in records:
            row = {k: '; '.join(v) if isinstance(v, list) else v for k, v in record.items()}
            # Avoid interpreting externally supplied metadata as spreadsheet formulas.
            row = {k: "'" + v if isinstance(v, str) and v.startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else v for k, v in row.items()}
            writer.writerow(row)
    temporary.replace(folder / 'results.csv')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, default=Path('education_review'))
    parser.add_argument('--start', type=date.fromisoformat)
    parser.add_argument('--end', type=date.fromisoformat)
    parser.add_argument('--max-pages', type=int, default=5, help='Pages per query per run (100 records/page); 0 removes the cap. Repeat to resume.')
    args = parser.parse_args()
    if args.max_pages < 0:
        parser.error('--max-pages must be nonnegative')
    folder = args.output.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    checkpoint = folder / 'checkpoint.json'
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text(encoding='utf-8'))
        if state.get('version') != 2 or state.get('search_field') != SEARCH_FIELD or state['queries'] != QUERIES:
            raise ValueError('Changed script/query strategy; choose another output folder.')
        for key in ('start', 'end'):
            supplied = getattr(args, key)
            if supplied and supplied.isoformat() != state[key]:
                raise ValueError('Changed dates; choose another output folder.')
    else:
        if (folder / 'results.json').exists() or (folder / 'results.csv').exists():
            raise ValueError('Outputs without checkpoint; choose another output folder.')
        start, end = args.start or date(2000, 1, 1), args.end or date.today()
        if start > end:
            parser.error('--start must not exceed --end')
        state = {'version': 2, 'search_field': SEARCH_FIELD, 'provider': 'OpenAlex', 'created_at': now(),
                 'start': start.isoformat(), 'end': end.isoformat(), 'queries': QUERIES,
                 'progress': {k: {'cursor': '*', 'complete': False, 'retrieved': 0} for k in QUERIES},
                 'audit': [], 'records': []}
        atomic_json(checkpoint, state)
    export(folder, state)
    try:
        for label, query in QUERIES.items():
            progress = state['progress'][label]
            pages = 0
            while not progress['complete'] and (args.max_pages == 0 or pages < args.max_pages):
                cursor = progress['cursor']
                data = request_page({'filter': f"{SEARCH_FIELD}:{query},from_publication_date:{state['start']},to_publication_date:{state['end']}",
                                     'cursor': cursor, 'per_page': 100})
                works = data['results']
                next_cursor = data['meta'].get('next_cursor')
                if works and next_cursor == cursor:
                    raise RuntimeError('API repeated cursor; stopped to avoid an infinite loop.')
                merge_works(state['records'], works, label)
                progress['retrieved'] += len(works)
                progress['cursor'] = next_cursor
                progress['complete'] = not works or not next_cursor
                state['audit'].append({'query_label': label, 'at': now(), 'cursor': cursor,
                                       'returned': len(works), 'reported_total': data['meta'].get('count')})
                atomic_json(checkpoint, state)
                pages += 1
                print(f"{label}: {progress['retrieved']} retrieved; {len(state['records'])} unique overall", flush=True)
                time.sleep(1)
    finally:
        export(folder, state)
    complete = all(p['complete'] for p in state['progress'].values())
    print('All query pages retrieved.' if complete else 'PARTIAL: page cap reached. Repeat the command to continue each unfinished query.')
    print(f"Saved {len(state['records'])} unique candidate records to {folder}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nInterrupted; repeat command to resume.', file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f'Stopped: {exc}', file=sys.stderr)
        sys.exit(1)