""" Offline parser tests against HTML saved by tools/capture_fixtures.py.

The saved pages change every time they are captured, so these tests check the shape of the
output (keys and types defined in docs/naming.md), not concrete values.
Tests are skipped when the fixtures have not been captured.
"""
import re

import pytest

from k2kparser import calendar

ISO_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
HHMM = re.compile(r'^\d{2}:\d{2}$')
WEEKDAYS = set('月火水木金土日')
BET_TYPES = {'win', 'place', 'wakuren', 'umaren', 'wide', 'umatan', 'trio', 'tierce'}
SURFACES = {'芝', 'ダート', '障害'}

# Keys that must not appear anymore (renamed in docs/naming.md)
OLD_KEYS = {
    'week_day', 'nichisuu', 'index', 'day', 'uma_num', 'dist', 'cond', 'odds_rank', 'win_fav', 'fav',
    'ninki', 'jokey', 'mare', 'bms', 'bmr', 'father', 'mother', 'mother_of_mother', 'hair',
    'pay_off', 'odds_params', 'links', 'vote', 'prev_url', 'next_url', 'params', 'number', 'candd',
    'rank', 'finish', 'flap', 'ftime', 'tag_', 'price', 'pay_back', 'indexes', 'bets', 'bet_price',
    'carried_over', 'carry_over', 'refresh', 'time', 'places', 'id', 'basic', 'weight', 'weight_diff',
    'course_cond', 'list', 'origin_of_name', 'breeding_center',
}


def walk(value, path=''):
    """ Yield (path, key, value) for every dict entry. """
    if isinstance(value, dict):
        for k, v in value.items():
            yield path, k, v
            yield from walk(v, '{}.{}'.format(path, k))
    elif isinstance(value, list):
        for v in value:
            yield from walk(v, path + '[]')


def assert_naming(output):
    for path, key, value in walk(output):
        assert key not in OLD_KEYS, 'old key {!r} at {}'.format(key, path or '.')
        if key == 'date':
            assert ISO_DATE.match(value), '{}.date = {!r}'.format(path, value)
        elif key == 'weekday':
            assert value in WEEKDAYS, '{}.weekday = {!r}'.format(path, value)
        elif key in ('departure', 'updated_at', 'closing_time_pat', 'closing_time_direct'):
            assert HHMM.match(value), '{}.{} = {!r}'.format(path, key, value)
        elif key in ('kai', 'nichi', 'race_num', 'horse_num', 'waku', 'distance', 'horse_count', 'popularity',
                     'age', 'body_weight', 'body_weight_diff', 'finish_time', 'last_3f', 'leg'):
            assert isinstance(value, int), '{}.{} = {!r}'.format(path, key, value)
        elif key in ('hande', 'win_odds'):
            assert isinstance(value, float), '{}.{} = {!r}'.format(path, key, value)
        elif key == 'surface':
            assert value in SURFACES, '{}.surface = {!r}'.format(path, value)
        elif key == 'link' or key.endswith('_link'):
            assert set(value) == {'url', 'param'}, '{}.{} = {!r}'.format(path, key, value)
        elif key in ('jockey', 'trainer'):
            assert isinstance(value, dict) and 'name' in value, '{}.{} = {!r}'.format(path, key, value)
        elif key == 'place':
            # 'place' is only the bet type 複勝 (never 競馬場 / 着順)
            assert not isinstance(value, str), '{}.place = {!r}'.format(path, value)


def assert_kaisai_days(days):
    assert days
    for day in days:
        assert {'date', 'weekday', 'kaisai'} <= set(day)
        for kaisai in day['kaisai']:
            assert {'kai', 'racecourse', 'nichi', 'link'} <= set(kaisai)


# ---- 開催一覧のトップ ----

@pytest.mark.parametrize('label', ['den_top', 'odds_top', 'result_top', 'result_kaisai_list'])
def test_kaisai_top(parse, label):
    days = parse(label)
    assert_naming(days)
    assert_kaisai_days(days)


def test_result_kaisai_list_year_from_link(parse):
    # 過去の結果一覧は年がページにない。リンクの日付から年を取る（今年で補わない）
    days = parse('result_kaisai_list')
    for day in days:
        param = day['kaisai'][0]['link']['param']
        assert day['date'].replace('-', '') in param


# ---- 開催ごとのレース一覧 ----

@pytest.mark.parametrize('label', ['den_kaisai', 'odds_kaisai', 'result_kaisai'])
def test_kaisai_races(parse, label):
    kaisai = parse(label)
    assert_naming(kaisai)
    assert {'date', 'weekday', 'kai', 'racecourse', 'nichi', 'races'} <= set(kaisai)
    assert kaisai['races']
    assert [r['race_num'] for r in kaisai['races']] == sorted(r['race_num'] for r in kaisai['races'])
    for race in kaisai['races']:
        assert {'race_num', 'name', 'condition'} <= set(race)
        if label == 'odds_kaisai':
            assert set(race['odds_links']) <= BET_TYPES
        else:
            assert {'surface', 'distance', 'link'} <= set(race)


# ---- 1レース ----

RACE_HEADER = {'date', 'weekday', 'kai', 'racecourse', 'nichi', 'race_num', 'departure', 'name',
               'distance', 'surface', 'course'}


def test_den_race(parse):
    race = parse('den_race')
    assert_naming(race)
    assert RACE_HEADER <= set(race)
    assert race['horses']
    for horse in race['horses']:
        assert {'name', 'sire', 'dam', 'broodmare_sire', 'jockey', 'trainer', 'age', 'sex'} <= set(horse)
        assert '母' not in horse['dam'] and '(' not in horse['dam']


def test_result_race(parse):
    race = parse('result_race')
    assert_naming(race)
    assert RACE_HEADER | {'weather', 'track_condition', 'horses', 'payouts'} <= set(race)
    assert race['course'].startswith(race['surface'][0])
    assert set(race['payouts']) <= BET_TYPES
    for lines in race['payouts'].values():
        for line in lines:
            assert {'combination', 'payout'} <= set(line)
    positions = [h['finish_position'] for h in race['horses'] if h['finish_position'] is not None]
    assert positions == sorted(positions)
    for horse in race['horses']:
        if horse['finish_position'] is None:
            assert horse['finish_status']
    # 映像のボタンは遅れて追加されることがあるので、ある場合だけ確認する
    for kind, entry in race.get('videos', {}).items():
        assert kind in ('race', 'patrol')
        assert set(entry) == {'video_id', 'contract_company_no'}   # parse_html だけでは CDN にアクセスしない
        assert entry['video_id'].startswith(race['date'][:4])


# ---- オッズ ----

@pytest.mark.parametrize('label', ['odds_tanpuku', 'odds_wakuren', 'odds_umaren', 'odds_wide',
                                   'odds_umatan', 'odds_trio', 'odds_tierce'])
def test_odds(parse, label):
    odds = parse(label)
    assert_naming(odds)
    assert set(odds['odds_links']) <= BET_TYPES
    assert odds['odds']
    if label == 'odds_tanpuku':
        for horse in odds['odds']:
            assert {'waku', 'horse_num', 'win', 'place'} <= set(horse)
    else:
        n = 3 if label in ('odds_trio', 'odds_tierce') else 2
        for combination, value in odds['odds'].items():
            assert len(combination.split('-')) == n
            if label == 'odds_wide':
                assert value is None or set(value) == {'min', 'max'}
            else:
                assert value is None or isinstance(value, float)


def test_odds_tierce_count(parse):
    # 3連単は 頭数 x (頭数-1) x (頭数-2) 通り（票数なしも None で残す）
    odds = parse('odds_tierce')
    horses = {int(c.split('-')[0]) for c in odds['odds']}
    n = len(horses)
    assert len(odds['odds']) == n * (n - 1) * (n - 2)


# ---- WIN5 ----

@pytest.mark.parametrize('label', ['win5', 'win5_past'])
def test_win5(parse, label):
    win5 = parse(label)
    assert_naming(win5)
    assert len(win5['races']) == 5
    assert [r['leg'] for r in win5['races']] == [1, 2, 3, 4, 5]
    for race in win5['races']:
        assert {'racecourse', 'race_num', 'name', 'link'} <= set(race)


def test_win5_result(parse):
    win5 = parse('win5_past')
    if 'winning_combination' not in win5:
        pytest.skip('captured WIN5 has no result')
    nums = [str(r['winner']['horse_num']) for r in win5['races']]
    assert win5['winning_combination'] == '-'.join(nums)


# ---- 馬・検索・その他 ----

def test_uma(parse):
    uma = parse('uma')
    assert_naming(uma)
    assert uma['name']
    assert {'sire', 'dam', 'broodmare_sire', 'sex', 'birthday', 'trainer'} <= set(uma['profile'])
    races = [r for r in uma['races'] if r['type'] == 'race']
    assert races
    for race in races:
        assert {'date', 'racecourse', 'name', 'distance', 'surface'} <= set(race)
        # 勝ち馬の欄にレーティングなどの数字が入っていないこと（列ずれの検出）
        for key in ('winner', 'runner_up'):
            if key in race:
                assert not race[key].isdigit()


def test_search(parse):
    umas = parse('search')
    assert_naming(umas)
    assert umas, 'search returned nothing (page layout changed?)'
    for uma in umas:
        assert {'active', 'name', 'link', 'sex'} <= set(uma)
        assert isinstance(uma['active'], bool)


def test_kaisai(parse):
    kaisai = parse('kaisai')
    assert_naming(kaisai)
    assert kaisai['racecourses']
    for rc in kaisai['racecourses']:
        assert rc['racecourse']


def test_top(parse):
    items = parse('top')
    assert_naming(items)
    tags = {item['tag'] for item in items}
    assert tags <= {'kaisai', 'den', 'odds', 'payout', 'result', 'tokubetsu', 'search'}
    assert {'den', 'odds', 'result'} <= tags


def test_tokubetsu(parse):
    days = parse('tokubetsu_top')
    assert_naming(days)
    for day in days:
        for kaisai in day['kaisai']:
            assert {'kai', 'racecourse', 'nichi', 'races'} <= set(kaisai)
            for race in kaisai['races']:
                assert {'name', 'distance', 'link'} <= set(race)
    horses = parse('tokubetsu_race')
    assert_naming(horses)
    assert horses and all('hande' in h for h in horses)


def test_calendar_month(parse):
    kaisais = parse('calendar_month')
    assert_naming(kaisais)
    for kaisai in kaisais:
        assert {'kai', 'racecourse', 'nichi', 'races'} <= set(kaisai)
        for race in kaisai['races']:
            assert {'race_num', 'name', 'class', 'distance', 'surface', 'departure'} <= set(race)


def test_calendar(parse, monkeypatch):
    # Do not fetch each day: return a marker instead
    monkeypatch.setattr(calendar.ParserCalendar, 'fetch_day', lambda self, day: [{'day': day}])
    days = parse('calendar', year=2026, month=11)
    assert days
    for day in days:
        assert ISO_DATE.match(day['date']) and day['weekday'] in WEEKDAYS
        assert day['kaisai'] == [{'day': int(day['date'][-2:])}]
