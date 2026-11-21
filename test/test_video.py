""" Tests of k2kparser.video (no network: CDN responses are faked). """
import json

import pytest
from bs4 import BeautifulSoup

from k2kparser import video, result

META = 'metaDataResult({});'.format(json.dumps({'movie': {
    'title': '202605080504.mp4', 'duration': '126',
    'movie_list_hls': [
        {'text': 'hq', 'url': 'jmc_pd/00372/abc/abc_8.m3u8'},
        {'text': 'auto', 'url': 'jmc_pd/00372/abc.m3u8'},
    ]}}))
MASTER = '\n'.join([
    '#EXTM3U',
    '#EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=480x270',
    'abc_6.m3u8',
    '#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=854x480',
    'abc_8.m3u8',
    '#EXT-X-STREAM-INF:BANDWIDTH=1000001,RESOLUTION=854x480',
    'abc_8b.m3u8',
])


@pytest.fixture
def fake_cdn(monkeypatch):
    responses = {}
    requested = []

    def fetch(url):
        requested.append(url)
        if url not in responses:
            raise video.VideoError('fetch failed: ' + url)
        return responses[url]

    monkeypatch.setattr(video, '_fetch', fetch)
    return responses, requested


BASE2 = video.cdn_base_url(2)


def meta_url(video_id, contract_company_no=2):
    return video.cdn_base_url(contract_company_no) + video.META_PATH.format(video_id)


def test_parse_video_ids():
    soup = BeautifulSoup("""
        <div class="movie_line"><script>eqPlayerButtonByAccount('202605080504', 2);</script></div>
        <div class="cell option"><ul><script>eqPlayerButtonByAccount('202605080504a', 2);</script></ul></div>
        <script>other();</script>""", 'html.parser')
    assert video.parse_video_ids(soup) == {
        'race': {'video_id': '202605080504', 'contract_company_no': 2},
        'patrol': {'video_id': '202605080504a', 'contract_company_no': 2},
    }


def test_parse_video_ids_past_page():
    # Past result pages use eqPlayerButton() without 'ByAccount'
    soup = BeautifulSoup("""
        <div class="movie_line"><script>eqPlayerButton('202203040503');</script></div>
        <script>eqPlayerButton('202203040503a');</script>""", 'html.parser')
    assert video.parse_video_ids(soup) == {
        'race': {'video_id': '202203040503', 'contract_company_no': 1},
        'patrol': {'video_id': '202203040503a', 'contract_company_no': 1},
    }


@pytest.mark.parametrize('script, expected', [
    ("eqPlayerButtonByAccount('202605080504', 2);", 2),
    ("eqPlayerButtonByAccount('202605080504', 1, true);", 1),
    ("eqPlayerButtonByAccount('202605080504');", 1),
    ("eqPlayerButton('202605080504', false, 2);", 2),
    ("eqPlayerButton('202605080504', true);", 1),
])
def test_contract_company_no(script, expected):
    soup = BeautifulSoup('<script>{}</script>'.format(script), 'html.parser')
    assert video.parse_video_ids(soup)['race']['contract_company_no'] == expected


def test_parse_video_ids_before_buttons_are_added():
    soup = BeautifulSoup('<div class="movie_line"><div class="btn_block"></div></div>', 'html.parser')
    assert video.parse_video_ids(soup) == {}


def test_get_hls(fake_cdn):
    responses, requested = fake_cdn
    responses[meta_url('202605080504')] = META
    responses[BASE2 + 'jmc_pd/00372/abc.m3u8'] = MASTER

    assert video.get_hls('202605080504', 2) == {
        'master_url': BASE2 + 'jmc_pd/00372/abc.m3u8',
        'resolutions': ['480x270', '854x480'],
        'duration': 126,
    }
    assert len(requested) == 2


@pytest.mark.parametrize('meta', ['<html>not found</html>', 'metaDataResult({"movie": {}});',
                                  'metaDataResult({"movie": {"movie_list_hls": []}});'])
def test_get_hls_bad_metadata(fake_cdn, meta):
    responses, _ = fake_cdn
    responses[meta_url('202605080504')] = meta
    with pytest.raises(video.VideoError):
        video.get_hls('202605080504', 2)


def test_get_hls_uses_cdn_of_contract_company(fake_cdn):
    responses, requested = fake_cdn
    with pytest.raises(video.VideoError):
        video.get_hls('202203040503', 1)
    assert requested == [meta_url('202203040503', 1)]
    assert 'eqd109zrse' in requested[0]
    with pytest.raises(video.VideoError):
        video.get_hls('202203040503', 9)          # unknown company


def test_get_hls_bad_master(fake_cdn):
    responses, _ = fake_cdn
    responses[meta_url('202605080504')] = META
    responses[BASE2 + 'jmc_pd/00372/abc.m3u8'] = '<html>error</html>'
    with pytest.raises(video.VideoError):
        video.get_hls('202605080504', 2)


def test_resolve_videos_keeps_id_when_not_available(fake_cdn):
    responses, _ = fake_cdn
    responses[meta_url('202605080504')] = META
    responses[BASE2 + 'jmc_pd/00372/abc.m3u8'] = MASTER
    videos = {'race': {'video_id': '202605080504', 'contract_company_no': 2},
              'patrol': {'video_id': '202605080504a', 'contract_company_no': 2}}

    video.resolve_videos(videos)

    assert videos['race']['master_url'].endswith('abc.m3u8')
    assert videos['patrol'] == {'video_id': '202605080504a', 'contract_company_no': 2}   # not on the CDN yet


@pytest.mark.parametrize('fetch_video, expected_calls', [(False, 0), (True, 1)])
def test_result_race_fetch_video_option(monkeypatch, fetch_video, expected_calls):
    calls = []
    monkeypatch.setattr(result.parser.ParserPost, 'parse',
                        lambda self: {'videos': {'race': {'video_id': '202605080504'}}})
    monkeypatch.setattr(video, 'resolve_videos', lambda videos: calls.append(videos))

    result.ParserResultRace('/JRADB/accessS.html', 'pw01sde0108202605050420261121/AE',
                            fetch_video=fetch_video).parse()

    assert len(calls) == expected_calls
