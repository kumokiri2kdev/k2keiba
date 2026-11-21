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
