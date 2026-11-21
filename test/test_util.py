""" Unit tests of k2kparser.util helpers (no fixtures needed). """
import pytest

from k2kparser import util


@pytest.mark.parametrize('text, year, expected', [
    ('2026年11月21日（土曜）', None, '2026-11-21'),
    ('2026年1月5日', None, '2026-01-05'),
    ('11月21日（土曜）', 2025, '2025-11-21'),
    ('2024.3.9', None, '2024-03-09'),
])
def test_to_iso_date(text, year, expected):
    assert util.to_iso_date(text, year=year) == expected


def test_to_iso_date_without_year_uses_this_year():
    import datetime
    assert util.to_iso_date('1月2日').startswith(str(datetime.datetime.now(util.JST).year))


def test_to_iso_date_error():
    with pytest.raises(util.UtilError):
        util.to_iso_date('no date')


@pytest.mark.parametrize('text, expected', [('（土曜）', '土'), ('（日）', '日'), ('月曜日', '月'), ('', None)])
def test_parse_weekday(text, expected):
    assert util.parse_weekday(text) == expected


@pytest.mark.parametrize('text, expected', [('15時01分', '15:01'), ('9時5分', '09:05'), ('15:40', '15:40'), ('', None)])
def test_to_hhmm(text, expected):
    assert util.to_hhmm(text) == expected


@pytest.mark.parametrize('text, expected', [
    ('5回東京8日', {'kai': 5, 'racecourse': '東京', 'nichi': 8}),
    ('3回\n福島\n5日', {'kai': 3, 'racecourse': '福島', 'nichi': 5}),
    ('5回東京', {'kai': 5, 'racecourse': '東京'}),
])
def test_parse_kaisai_name(text, expected):
    assert util.parse_kaisai_name(text) == expected


def test_parse_kaisai_header():
    assert util.parse_kaisai_header('2026年11月21日（土曜） 5回京都5日') == {
        'date': '2026-11-21', 'weekday': '土', 'kai': 5, 'racecourse': '京都', 'nichi': 5}


@pytest.mark.parametrize('param, date, expected', [
    ('pw01srl10052025040120251004/45', '2026-10-04', 2025),
    ('pw15orl00032026030520261121/xx', '2026-11-21', 2026),
    ('pw01dli00/F3', '2026-11-21', None),
])
def test_year_from_param(param, date, expected):
    assert util.year_from_param(param, date) == expected


@pytest.mark.parametrize('text, expected', [
    ('ダート・右', 'ダート'), ('ダ', 'ダート'), ('芝・左 外', '芝'), ('障害・芝', '障害'), ('?', None)])
def test_parse_surface(text, expected):
    assert util.parse_surface(text) == expected


def test_parse_numbers():
    assert util.parse_int('1,234円') == 1234
    assert util.parse_int('取消') is None
    assert util.parse_float('57.0kg') == 57.0
    assert util.parse_float('取消') is None


@pytest.mark.parametrize('text, expected', [
    ('武 英智(栗東)', {'name': '武 英智', 'affiliation': '栗東'}),
    ('武 英智（栗東）', {'name': '武 英智', 'affiliation': '栗東'}),
    ('C.ルメール', {'name': 'C.ルメール'}),
])
def test_person(text, expected):
    assert util.person(text) == expected


@pytest.mark.parametrize('text, expected', [('1:09.3', 693), ('34.5', 345), ('2:00.1', 1201), ('0.7', 7)])
def test_parse_race_time(text, expected):
    assert util.Util.parse_race_time(text) == expected


def test_normalize_coat():
    assert util.normalize_coat('黒鹿毛') == '黒鹿'
    assert util.normalize_coat('栗') == '栗'


# Real parameters taken from JRA pages (one per kind)
@pytest.mark.parametrize('param', [
    'pw01dli00/F3',                              # 出馬表トップ
    'pw01skl10202510/1E',                        # 過去のレース結果（月）
    'pw01skl00999999/B3',                        # 過去のレース結果検索
    'pw01srl10052025040120251004/45',            # 過去の開催
    'pw01sde0108202605050420261121/AE',          # レース結果
    'pw01dde0108202605051120261121/25',          # 出馬表
    'pw01dud002022103614/A5',                    # 馬
    'pw04kmk001102/90',                          # 騎手
    'pw05cmk001161/C9',                          # 調教師
    'pw17hde01202611211/EF',                     # WIN5
    'pw151ouS308202605051120261121Z/C8',         # オッズ（単複）
    'pw157ouS308202605051120261121Z99/42',       # オッズ（3連複, 32文字）
])
def test_param_checksum(param):
    head, tail = param.split('/')
    assert util.param_checksum(head) == tail
    assert util.make_param(head) == param


def test_param_checksum_all_captured_links():
    """ Every link in the saved pages has the checksum computed by param_checksum(). """
    import glob
    import os
    import re
    from .conftest import FIXTURE_DIR
    files = glob.glob(os.path.join(FIXTURE_DIR, '*.html'))
    if not files:
        pytest.skip('fixtures not captured')
    params = set()
    for path in files:
        with open(path, encoding='utf-8') as f:
            params.update(re.findall(r"(p[wj]\d{2}[a-z0-9]{3}[0-9A-Za-z]{2,40})(?:/|%2F)([0-9A-F]{2})(?![0-9A-Za-z])", f.read()))
    assert len(params) > 300
    wrong = [(head, tail) for head, tail in params if util.param_checksum(head) != tail]
    assert wrong == []


@pytest.mark.parametrize('convert, param, expected', [
    (util.Util.convert_resul_param_as_past, 'pw01sde0108202605050420261121/AE', 'pw01sde1008202605050420261121/8D'),
    (util.Util.convert_resul_param_as_past, 'pw01sde1008202605050420261121/8D', 'pw01sde1008202605050420261121/8D'),
    (util.Util.convert_horse_param_as_past, 'pw01dud002022103614/A5', 'pw01dud102022103614/8C'),
])
def test_convert_param_as_past(convert, param, expected):
    assert convert(param) == expected
