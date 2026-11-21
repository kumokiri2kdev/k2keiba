""" Tests of k2kparser.result_params and tools/update_result_params.py (no network). """
import json
import os
import sys
from urllib.parse import parse_qs

import pytest

from k2kparser import parser, result_params, result_params_data
from .conftest import FIXTURE_DIR

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import update_result_params as tool      # noqa: E402

TABLE = {'2510': '1E', '2511': 'EC', '9001': 'E1'}


@pytest.mark.parametrize('yyyymm, year_month, expected', [
    (202510, 202511, 'pw01skl10202510/1E'),     # before yearMonth: fixed
    (202511, 202511, 'pw01skl00202511/EC'),     # yearMonth and later: not fixed
    (199001, 202511, 'pw01skl10199001/E1'),     # 1990s
    (202701, 202511, None),                     # not in the table yet
])
def test_get_cname(yyyymm, year_month, expected):
    assert result_params.ParserRaceParams.get_cname(yyyymm, params=TABLE, year_month=year_month) == expected


def test_get_cname_with_saved_table():
    # Past months never change; these were also in the hand-written table before
    assert result_params.ParserRaceParams.get_cname(202510) == 'pw01skl10202510/1E'
    assert result_params.ParserRaceParams.get_cname(200001) == 'pw01skl10200001/AD'
    assert result_params.ParserRaceParams.get_cname(198601) == 'pw01skl10198601/BE'


def test_saved_table_is_complete():
    keys = set(result_params_data.PARAMS)
    first_year, last_year = 1986, result_params_data.YEAR_MONTH // 100
    for year in range(first_year, last_year + 1):
        for month in range(1, 13):
            assert '{:02d}{:02d}'.format(year % 100, month) in keys


def test_is_fixed():
    assert result_params.ParserRaceParams.is_fixed('pw01skl10202510/1E')
    assert not result_params.ParserRaceParams.is_fixed('pw01skl00202611/91')


def test_parse_page():
    """ Any past result page has the objParam script. """
    meta_path = os.path.join(FIXTURE_DIR, 'result_kaisai_list.meta.json')
    if not os.path.exists(meta_path):
        pytest.skip('fixture not captured: result_kaisai_list')
    with open(os.path.join(FIXTURE_DIR, 'result_kaisai_list.html'), encoding='utf-8') as f:
        html = f.read()

    table = result_params.ParserResultParams.__new__(result_params.ParserResultParams).parse_html(html)

    assert table['year_month'] // 100 >= 2026
    assert len(table['params']) >= tool.MIN_ENTRIES
    # The CNAME used to open this page is reproduced from the table
    with open(meta_path, encoding='utf-8') as f:
        cname = parse_qs(json.load(f)['param'])['cname'][0]
    yyyymm = int(cname[9:15])
    assert result_params.ParserRaceParams.get_cname(
        yyyymm, params=table['params'], year_month=table['year_month']) == cname


def test_parse_page_without_script():
    p = result_params.ParserResultParams.__new__(result_params.ParserResultParams)
    with pytest.raises(parser.ParseError):
        p.parse_html('<html><script>var x = 1;</script></html>')


def test_render_roundtrip():
    table = {'year_month': 202611, 'params': {'2611': '91', '8601': 'BE', '0001': 'AD', '9912': '48'}}
    namespace = {}
    exec(tool.render(table, 'test', '2026-11-21'), namespace)
    assert namespace['YEAR_MONTH'] == 202611
    assert namespace['PARAMS'] == table['params']
    # Ordered by year: 1986, 1999, 2000, 2026
    assert list(namespace['PARAMS']) == ['8601', '9912', '0001', '2611']
