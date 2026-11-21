""" Tests of k2kparser.result_params (no network). """
import json
import os
from urllib.parse import parse_qs

import pytest

from k2kparser import parser, result_params, util
from .conftest import FIXTURE_DIR


@pytest.mark.parametrize('yyyymm, year_month, expected', [
    (202510, 202611, 'pw01skl10202510/1E'),     # before yearMonth: fixed
    (202611, 202611, 'pw01skl00202611/91'),     # yearMonth and later: not fixed
    (202612, 202611, 'pw01skl00202612/5F'),
    (199001, 202611, 'pw01skl10199001/E1'),     # 1990s
    (198601, 202611, 'pw01skl10198601/BE'),
])
def test_get_cname(yyyymm, year_month, expected):
    # Expected values are from JRA's objParam table (2026-11-21)
    assert result_params.ParserRaceParams.get_cname(yyyymm, year_month=year_month) == expected


def test_get_cname_uses_this_month(monkeypatch):
    monkeypatch.setattr(result_params, 'this_month', lambda: 202611)
    assert result_params.ParserRaceParams.get_cname(202610) == 'pw01skl10202610/AA'
    assert result_params.ParserRaceParams.get_cname(202611) == 'pw01skl00202611/91'
    assert result_params.ParserRaceParams.get_cname(202701).startswith('pw01skl00202701/')


def test_is_fixed():
    assert result_params.ParserRaceParams.is_fixed('pw01skl10202510/1E')
    assert not result_params.ParserRaceParams.is_fixed('pw01skl00202611/91')


def _past_page():
    meta_path = os.path.join(FIXTURE_DIR, 'result_kaisai_list.meta.json')
    if not os.path.exists(meta_path):
        pytest.skip('fixture not captured: result_kaisai_list')
    with open(os.path.join(FIXTURE_DIR, 'result_kaisai_list.html'), encoding='utf-8') as f:
        html = f.read()
    with open(meta_path, encoding='utf-8') as f:
        cname = parse_qs(json.load(f)['param'])['cname'][0]
    return html, cname


def test_formula_matches_jra_table():
    """ The whole objParam table of JRA's page is reproduced by util.param_checksum(). """
    html, _ = _past_page()
    table = result_params.ParserResultParams.__new__(result_params.ParserResultParams).parse_html(html)
    assert len(table['params']) >= 12 * 30

    for yymm, expected in table['params'].items():
        yy = int(yymm[:2])
        yyyymm = (1900 + yy if yy >= 80 else 2000 + yy) * 100 + int(yymm[2:])
        cname = result_params.ParserRaceParams.get_cname(yyyymm, year_month=table['year_month'])
        assert cname[-2:] == expected, yymm


def test_cname_of_captured_page():
    _, cname = _past_page()
    yyyymm = int(cname[9:15])
    assert result_params.ParserRaceParams.get_cname(yyyymm, year_month=999999) == cname


def test_parse_page_without_script():
    p = result_params.ParserResultParams.__new__(result_params.ParserResultParams)
    with pytest.raises(parser.ParseError):
        p.parse_html('<html><script>var x = 1;</script></html>')
