""" Tests of the MCP server (k2kmcp) against the pages saved by tools/capture_fixtures.py.

Parser.afetch is replaced so that nothing is sent to JRA. The tool arguments (date, racecourse,
race number) are taken from the saved pages, so the tests keep working after re-capturing.
"""
import asyncio
import glob
import json
import os
import re
from urllib.parse import parse_qs

import pytest

pytest.importorskip('mcp')
from mcp import Client      # noqa: E402

from k2kparser import parser          # noqa: E402
from k2kmcp import server as mcp_server, navigator   # noqa: E402
from .conftest import FIXTURE_DIR, parse_fixture      # noqa: E402


def _pages():
    """ (path, cname or None) -> body of the saved pages """
    pages = {}
    for meta_path in glob.glob(os.path.join(FIXTURE_DIR, '*.meta.json')):
        label = os.path.basename(meta_path)[:-len('.meta.json')]
        with open(meta_path, encoding='utf-8') as f:
            meta = json.load(f)
        ext = 'json.txt' if meta['class'] == 'ParserCalendar' else 'html'
        with open(os.path.join(FIXTURE_DIR, '{}.{}'.format(label, ext)), encoding='utf-8') as f:
            body = f.read()
        cname = parse_qs(meta['param'])['cname'][0] if meta['param'] else None
        pages[(meta['uri'].replace(parser.JRA_BASE_URL, ''), cname)] = body
    return pages


@pytest.fixture
def call(monkeypatch):
    if not os.path.exists(os.path.join(FIXTURE_DIR, 'den_top.meta.json')):
        pytest.skip('fixtures not captured (run tools/capture_fixtures.py)')
    pages = _pages()
    requested = []

    async def afetch(self, client=None):
        cname = parse_qs(self.data.decode())['cname'][0] if self.method == 'POST' else None
        key = (self.uri.replace(parser.JRA_BASE_URL, ''), cname)
        requested.append(key)
        if key not in pages:
            raise parser.ParseErrorHTTP(404)
        return pages[key]

    monkeypatch.setattr(parser.Parser, 'afetch', afetch)
    monkeypatch.setattr(mcp_server, 'navigator', navigator.Navigator())     # empty cache per test

    def run(name, arguments=None):
        async def main():
            async with Client(mcp_server.server) as client:
                return await client.call_tool(name, arguments or {})
        return asyncio.run(main())

    run.requested = requested
    run.pages = pages
    return run


def _no_links(value):
    text = json.dumps(value, ensure_ascii=False)
    assert '"link"' not in text and '"param"' not in text and '_link' not in text


def _odds_race():
    """ (date, racecourse, race_num) of the saved odds pages (see capture_fixtures.py) """
    kaisai = parse_fixture('odds_kaisai')
    race = next((r for r in kaisai['races'] if r['race_num'] == 11), kaisai['races'][-1])
    return kaisai['date'], kaisai['racecourse'], race['race_num']


# ---- tools ----

def test_list_tools():
    async def main():
        async with Client(mcp_server.server) as client:
            return await client.list_tools()
    tools = {t.name: t for t in asyncio.run(main()).tools}
    assert set(tools) == {'list_meetings', 'get_track_conditions', 'list_races', 'get_race_card', 'get_odds',
                          'get_race_result', 'search_horses', 'get_horse', 'compare_bets'}
    for tool in tools.values():
        assert tool.description
        assert tool.annotations.read_only_hint is True
        # no $ref: some clients (e.g. Codex) may not resolve references
        assert '$ref' not in json.dumps(tool.input_schema)
    bet = tools['compare_bets'].input_schema['properties']['strategies']['items']['properties']['bets']['items']
    assert {'bet_type', 'formation', 'box', 'combinations', 'amount'} <= set(bet['properties'])


def test_list_meetings(call):
    r = call('list_meetings')
    assert not r.is_error
    days = r.structured_content['days']
    assert [d['date'] for d in days] == [d['date'] for d in parse_fixture('den_top')]
    assert {'racecourse', 'kai', 'nichi'} <= set(days[0]['meetings'][0])


def test_list_races(call):
    kaisai = parse_fixture('den_kaisai')
    r = call('list_races', {'date': kaisai['date'], 'racecourse': kaisai['racecourse']})
    assert not r.is_error
    assert r.structured_content['source'] == 'race_card'
    assert len(r.structured_content['races']) == len(kaisai['races'])
    _no_links(r.structured_content)


def test_list_races_romanized_racecourse(call):
    kaisai = parse_fixture('den_kaisai')
    roman = {v: k for k, v in navigator.RACECOURSE_ALIASES.items()}[kaisai['racecourse']]
    r = call('list_races', {'date': kaisai['date'], 'racecourse': roman.capitalize()})
    assert not r.is_error


def test_get_race_card(call):
    card = parse_fixture('den_race')
    r = call('get_race_card', {'date': card['date'], 'racecourse': card['racecourse'], 'race_num': card['race_num']})
    assert not r.is_error
    out = r.structured_content
    assert out['name'] == card['name']
    assert len(out['horses']) == len(card['horses'])
    for horse in out['horses']:
        assert re.fullmatch(r'\d{10}', horse['horse_id'])
    _no_links(out)


def test_get_odds_win(call):
    date, racecourse, race_num = _odds_race()
    r = call('get_odds', {'date': date, 'racecourse': racecourse, 'race_num': race_num, 'horse_nums': [1, 2]})
    assert not r.is_error
    assert [h['horse_num'] for h in r.structured_content['odds']] == [1, 2]


def test_get_odds_combinations(call):
    date, racecourse, race_num = _odds_race()
    r = call('get_odds', {'date': date, 'racecourse': racecourse, 'race_num': race_num,
                          'bet_type': 'tierce', 'horse_nums': [1], 'limit': 5})
    assert not r.is_error
    out = r.structured_content
    assert out['returned'] == 5 and out['matched_combinations'] >= 5
    for row in out['odds']:
        assert '1' in row['combination'].split('-')
    values = [row['odds'] for row in out['odds'] if row['odds'] is not None]
    assert values == sorted(values)


def test_get_odds_wide(call):
    date, racecourse, race_num = _odds_race()
    r = call('get_odds', {'date': date, 'racecourse': racecourse, 'race_num': race_num, 'bet_type': 'wide', 'limit': 3})
    assert not r.is_error
    assert {'combination', 'min', 'max'} == set(r.structured_content['odds'][0])


def test_compare_bets(call):
    date, racecourse, race_num = _odds_race()
    win = parse_fixture('odds_tanpuku')['odds']
    a, b, c, d = [h['horse_num'] for h in sorted(win, key=lambda h: h['win'] or 9999)][:4]
    strategies = [
        {'name': 'trio', 'bets': [{'bet_type': 'trio', 'formation': [[a], [b, c], [b, c, d]]}]},
        {'name': 'umaren', 'bets': [{'bet_type': 'umaren', 'formation': [[a], [b, c]]}]},
    ]
    r = call('compare_bets', {'date': date, 'racecourse': racecourse, 'race_num': race_num,
                              'strategies': strategies, 'table_size': 5})
    assert not r.is_error, r.content[0].text
    out = r.structured_content
    assert out['probability_source'] == 'tierce odds'
    assert [s['points'] for s in out['strategies']] == [3, 2]
    assert len(out['finishes']) <= 5
    # the odds pages of the race are fetched once each (trio, umaren, tierce)
    assert len([k for k in call.requested if k[1] and k[1].startswith('pw15') and 'ou' in k[1]]) == 3


def test_get_odds_past_race_via_result(call, monkeypatch):
    """ A race not in this week's odds list: result page -> its odds_link -> the bet type's page """
    race = parse_fixture('result_race')

    async def not_this_week(self, date, racecourse, race_num, kind):
        if kind == 'odds':
            raise navigator.NotFound('JRA publishes odds only for this week.')
        return await original(self, date, racecourse, race_num, kind)
    original = navigator.Navigator.race_entry
    monkeypatch.setattr(navigator.Navigator, 'race_entry', not_this_week)
    # serve the saved win odds page (its odds_links lead to the other saved odds pages) at the result's odds_link
    cname = race['odds_link']['param']
    with open(os.path.join(FIXTURE_DIR, 'odds_tanpuku.html'), encoding='utf-8') as f:
        call.pages[('/JRADB/accessO.html', cname)] = f.read()

    r = call('get_odds', {'date': race['date'], 'racecourse': race['racecourse'], 'race_num': race['race_num'],
                          'bet_type': 'trio', 'limit': 3})
    assert not r.is_error, r.content[0].text
    assert r.structured_content['returned'] == 3
    assert ('/JRADB/accessO.html', cname) in call.requested


def test_compare_bets_error(call):
    date, racecourse, race_num = _odds_race()
    r = call('compare_bets', {'date': date, 'racecourse': racecourse, 'race_num': race_num, 'budget': 100,
                              'strategies': [{'name': 'x', 'bets': [{'bet_type': 'umaren', 'box': [1, 2, 3]}]}]})
    assert r.is_error and 'not enough' in r.content[0].text


def test_get_race_result(call):
    race = parse_fixture('result_race')
    r = call('get_race_result', {'date': race['date'], 'racecourse': race['racecourse'], 'race_num': race['race_num']})
    assert not r.is_error
    out = r.structured_content
    assert out['horses'][0]['finish_position'] == race['horses'][0]['finish_position']
    assert out['payouts'] == race['payouts']
    assert 'horse_id' in out['horses'][0]
    _no_links(out)


def test_search_horses(call):
    r = call('search_horses', {'name': 'アイアン'})
    assert not r.is_error
    assert r.structured_content['count'] == len(parse_fixture('search'))
    assert re.fullmatch(r'\d{10}', r.structured_content['horses'][0]['horse_id'])


def test_get_horse(call):
    with open(os.path.join(FIXTURE_DIR, 'uma.meta.json'), encoding='utf-8') as f:
        cname = parse_qs(json.load(f)['param'])['cname'][0]
    horse_id = navigator.horse_id_of({'param': cname})
    r = call('get_horse', {'horse_id': horse_id, 'max_races': 2})
    assert not r.is_error
    out = r.structured_content
    assert out['name'] == parse_fixture('uma')['name']
    assert len(out['races']) <= 2
    _no_links(out)


def test_get_track_conditions(call):
    r = call('get_track_conditions')
    assert not r.is_error
    assert r.structured_content['racecourses']


# ---- errors (returned to the model as tool errors with a hint) ----

def test_error_racecourse_not_held(call):
    card = parse_fixture('den_race')
    other = next(rc for rc in ('東京', '中山', '京都', '阪神', '小倉') if rc != card['racecourse']
                 and all(m['racecourse'] != rc for d in parse_fixture('den_top') if d['date'] == card['date']
                         for m in d['kaisai']))
    r = call('get_race_card', {'date': card['date'], 'racecourse': other, 'race_num': 11})
    assert r.is_error
    assert 'Meetings that day' in r.content[0].text


def test_error_past_race_card(call):
    r = call('get_race_card', {'date': '2020-01-05', 'racecourse': '中山', 'race_num': 11})
    assert r.is_error
    assert 'only for this week' in r.content[0].text


@pytest.mark.parametrize('arguments, message', [
    ({'date': 'tomorrow', 'racecourse': '東京', 'race_num': 1}, 'Invalid date'),
    ({'date': '2026-11-21', 'racecourse': 'Osaka', 'race_num': 1}, 'Unknown racecourse'),
])
def test_error_bad_arguments(call, arguments, message):
    r = call('get_race_result', arguments)
    assert r.is_error
    assert message in r.content[0].text


def test_error_bad_horse_id(call):
    r = call('get_horse', {'horse_id': '123'})
    assert r.is_error and 'Invalid horse_id' in r.content[0].text


def test_list_pages_are_cached(call):
    card = parse_fixture('den_race')
    args = {'date': card['date'], 'racecourse': card['racecourse']}
    assert not call('list_races', args).is_error
    assert not call('get_race_card', {**args, 'race_num': card['race_num']}).is_error
    # The top list and the meeting page are fetched only once for the two calls
    assert len(call.requested) == len(set(call.requested)) == 3     # top, meeting, race card


# ---- HTTP transport ----

def test_transport_security_default():
    assert mcp_server.transport_security('127.0.0.1', []) is None      # SDK default (localhost only)


def test_transport_security_allow_host():
    s = mcp_server.transport_security('127.0.0.1', ['abc.trycloudflare.com'])
    assert s.enable_dns_rebinding_protection
    assert {'localhost:*', 'abc.trycloudflare.com'} <= set(s.allowed_hosts)
    assert 'https://abc.trycloudflare.com' in s.allowed_origins


def test_main_runs_http(monkeypatch):
    calls = []
    monkeypatch.setattr(mcp_server.server, 'run', lambda *a, **kw: calls.append((a, kw)))
    mcp_server.main(['--http', '--port', '9000', '--allow-host', 'abc.example.com'])
    (args, kwargs), = calls
    assert args == ('streamable-http',)
    assert kwargs['port'] == 9000 and 'abc.example.com' in kwargs['transport_security'].allowed_hosts


def test_main_allow_host_needs_http():
    with pytest.raises(SystemExit):
        mcp_server.main(['--allow-host', 'abc.example.com'])
