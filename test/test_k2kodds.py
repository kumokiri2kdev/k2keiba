""" Tests of k2kodds (no network). """
from itertools import permutations

import pytest

from k2kodds import compare, allocate, expand, outcomes_from_tierce, outcomes_from_win, OddsError
from .conftest import parse_fixture

# 4 runners, every finish equally likely (1/24): easy to count by hand
TIERCE_EVEN = {'-'.join(map(str, o)): 100.0 for o in permutations([1, 2, 3, 4], 3)}
WIN = [{'waku': w, 'horse_num': n, 'win': 4.0, 'place': None} for w, n in ((1, 1), (2, 2), (3, 3), (3, 4))]
ODDS = {
    'tierce': TIERCE_EVEN,
    'win': WIN,
    'umaren': {'1-2': 5.0, '1-3': 6.0, '1-4': 7.0, '2-3': 8.0, '2-4': 9.0, '3-4': 10.0},
    'wide': {'1-2': {'min': 2.0, 'max': 3.0}, '1-3': None},
    'trio': {'1-2-3': 4.0, '1-2-4': 4.0, '1-3-4': 4.0, '2-3-4': 4.0},
    'wakuren': {'1-2': 6.0, '1-3': 3.0, '3-3': 20.0},
}


def _run(bets, **kw):
    return compare([{'name': 's', 'bets': bets}], ODDS, **kw)['strategies'][0]


# ---- tickets ----

@pytest.mark.parametrize('bet, expected', [
    ({'bet_type': 'trio', 'formation': [[1], [2, 3], [2, 3, 4]]}, ['1-2-3', '1-2-4', '1-3-4']),
    ({'bet_type': 'umatan', 'box': [1, 2, 3]}, ['1-2', '1-3', '2-1', '2-3', '3-1', '3-2']),
    ({'bet_type': 'umaren', 'formation': [[2], [1, 3]]}, ['1-2', '2-3']),
    ({'bet_type': 'tierce', 'formation': [[1], [2, 3], [2, 3]]}, ['1-2-3', '1-3-2']),
    ({'bet_type': 'win', 'horses': [3, 1, 3]}, ['3', '1']),
    ({'bet_type': 'trio', 'combinations': ['3-2-1', '1-2-3']}, ['1-2-3']),
    ({'bet_type': 'wakuren', 'box': [3, 3]}, None),             # box of one bracket: too few
    ({'bet_type': 'wakuren', 'formation': [[3], [3]]}, ['3-3']),
])
def test_expand(bet, expected):
    if expected is None:
        with pytest.raises(OddsError):
            expand(bet)
    else:
        assert expand(bet) == expected


@pytest.mark.parametrize('bet', [
    {'bet_type': 'place', 'horses': [1]},
    {'bet_type': 'trio', 'formation': [[1], [2]]},
    {'bet_type': 'trio', 'formation': [[1], [1], [1]]},
    {'bet_type': 'umaren'},
    {'bet_type': 'umaren', 'combinations': ['1-2-3']},
])
def test_expand_errors(bet):
    with pytest.raises(OddsError):
        expand(bet)


# ---- allocation ----

def test_allocate_equal():
    assert allocate([2.0, 5.0, 10.0], 1000, 'equal') == [300, 300, 300]


def test_allocate_payout():
    amounts = allocate([2.0, 4.0], 3000, 'payout')
    assert sum(amounts) == 3000
    assert amounts == [2000, 1000]          # payout 4000 either way


def test_allocate_not_enough():
    with pytest.raises(OddsError):
        allocate([2.0] * 4, 300)


# ---- probabilities ----

def test_outcomes_from_tierce():
    p = outcomes_from_tierce({'1-2-3': 10.0, '2-1-3': 20.0, '3-2-1': None})
    assert p == pytest.approx({(1, 2, 3): 2 / 3, (2, 1, 3): 1 / 3})


def test_outcomes_from_win_harville():
    p = outcomes_from_win(WIN)
    assert sum(p.values()) == pytest.approx(1)
    assert p[(1, 2, 3)] == pytest.approx(1 / 24)


# ---- compare ----

def test_compare_counts_by_hand():
    r = _run([{'bet_type': 'umaren', 'combinations': ['1-2']}], budget=1000)
    assert r['hit_probability'] == pytest.approx(4 / 24, abs=1e-4)          # 1-2-x, 2-1-x
    assert r['payout_when_hit'] == {'min': 5000, 'median': 5000, 'max': 5000}
    assert r['return_when_hit']['max'] == 5.0

    r = _run([{'bet_type': 'win', 'horses': [1]}], budget=1000)
    assert r['hit_probability'] == pytest.approx(6 / 24, abs=1e-4)

    r = _run([{'bet_type': 'wide', 'combinations': ['1-2']}], budget=1000)
    assert r['hit_probability'] == pytest.approx(12 / 24, abs=1e-4)          # 1 and 2 in the first 3
    assert r['payout_when_hit']['max'] == 2000                               # wide='min'
    assert _run([{'bet_type': 'wide', 'combinations': ['1-2']}], budget=1000, wide='max')[
        'payout_when_hit']['max'] == 3000


def test_compare_torigami_and_profit():
    # trio box of 4 runners: always hits, 4 tickets x 100 yen, payout 400 = spent (neither)
    r = _run([{'bet_type': 'trio', 'box': [1, 2, 3, 4]}], budget=400)
    assert r['hit_probability'] == pytest.approx(1)
    assert r['profit_probability'] == 0 and r['torigami_probability'] == 0

    r = _run([{'bet_type': 'umaren', 'box': [1, 2, 3]}], budget=600)       # 3 tickets x 200 yen
    assert r['torigami_probability'] == 0
    r = _run([{'bet_type': 'umaren', 'box': [1, 2, 3, 4]}], budget=600)    # 6 tickets x 100 yen; 1-2 pays 500
    assert r['torigami_probability'] == pytest.approx(4 / 24, abs=1e-4)


def test_compare_wide_can_hit_three_tickets():
    odds = dict(ODDS, wide={'1-2': {'min': 2.0, 'max': 2.0}, '1-3': {'min': 3.0, 'max': 3.0},
                            '2-3': {'min': 4.0, 'max': 4.0}})
    r = compare([{'bets': [{'bet_type': 'wide', 'box': [1, 2, 3]}]}], odds, budget=300)['strategies'][0]
    assert r['payout_when_hit']['max'] == 900                # 1, 2 and 3 in the first 3: all three hit


def test_compare_excluded_and_fixed_amount():
    r = _run([{'bet_type': 'wide', 'combinations': ['1-2', '1-3']}, {'bet_type': 'win', 'horses': [5]}])
    assert [t['combination'] for t in r['tickets']] == ['1-2']
    assert {e['reason'] for e in r['excluded']} == {'no odds (cancelled or not sold)', 'horse not running'}

    r = _run([{'bet_type': 'win', 'horses': [1], 'amount': 1000}, {'bet_type': 'win', 'horses': [2, 3]}],
             budget=3000)
    assert [t['amount'] for t in r['tickets']] == [1000, 1000, 1000]


def test_compare_wakuren_uses_brackets():
    # horses 3 and 4 are both in bracket 3
    r = _run([{'bet_type': 'wakuren', 'combinations': ['3-3']}], budget=100)
    assert r['hit_probability'] == pytest.approx(4 / 24, abs=1e-4)


def test_compare_finish_table():
    r = compare([{'name': 'trio', 'bets': [{'bet_type': 'trio', 'combinations': ['1-2-3']}]},
                 {'name': 'umatan', 'bets': [{'bet_type': 'umaren', 'combinations': ['1-2']}]}], ODDS, budget=100)
    rows = {row['finish']: row['payouts'] for row in r['finishes']}
    # {1,2,3}: the orders split by whether 1 and 2 are 1st-2nd (umaren hits too)
    assert {'trio': 400, 'umatan': 500} in rows.values()
    assert {'trio': 400, 'umatan': 0} in rows.values()
    assert {'trio': 0, 'umatan': 500} in rows.values()            # 1-2-4 / 2-1-4
    assert sum(row['probability'] for row in r['finishes']) + r['no_hit_probability'] == pytest.approx(1, abs=1e-3)


def test_compare_any_order_label():
    r = compare([{'bets': [{'bet_type': 'trio', 'combinations': ['1-2-3']}]}], ODDS, budget=100)
    assert r['finishes'][0]['finish'] == '1-2-3 (any order)'
    assert r['finishes'][0]['probability'] == pytest.approx(0.25)


def test_compare_errors():
    with pytest.raises(OddsError):
        compare([], ODDS)
    with pytest.raises(OddsError):
        compare([{'bets': [{'bet_type': 'umatan', 'box': [1, 2]}]}], ODDS)     # no umatan odds given
    with pytest.raises(OddsError):
        compare([{'bets': [{'bet_type': 'win', 'horses': [1]}]}], ODDS, wide='avg')


# ---- with k2kparser's output (the shape k2kodds expects) ----

def test_compare_with_parsed_odds():
    odds = {t: parse_fixture(label)['odds'] for t, label in (
        ('win', 'odds_tanpuku'), ('wakuren', 'odds_wakuren'), ('umaren', 'odds_umaren'), ('wide', 'odds_wide'),
        ('umatan', 'odds_umatan'), ('trio', 'odds_trio'), ('tierce', 'odds_tierce'))}
    favorites = [h['horse_num'] for h in sorted(odds['win'], key=lambda h: h['win'] or 9999)][:3]
    strategies = [{'name': bt, 'bets': [{'bet_type': bt, 'box': favorites[:3]}]}
                  for bt in ('win', 'umaren', 'wide', 'umatan', 'trio', 'tierce')]
    brackets = list(range(1, 9))     # every bracket pair including the same bracket (e.g. 7-7)
    strategies.append({'name': 'wakuren',
                       'bets': [{'bet_type': 'wakuren', 'formation': [brackets, brackets], 'amount': 100}]})
    r = compare(strategies, odds, budget=3000)
    for s in r['strategies']:
        assert 0 < s['hit_probability'] <= 1, s['name']
        assert s['tickets'] and s['spent'] <= 3600
    by_name = {s['name']: s for s in r['strategies']}
    # covering more finishes: wide box >= umaren box >= umatan box
    assert by_name['wide']['hit_probability'] >= by_name['umaren']['hit_probability'] \
        >= by_name['umatan']['hit_probability']
    assert by_name['trio']['hit_probability'] == pytest.approx(by_name['tierce']['hit_probability'], abs=1e-3)
    assert by_name['wakuren']['hit_probability'] > 0.99
