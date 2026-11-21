""" Tests of the async API (k2kparser.aio and aparse()).

A local aiohttp server stands in for the JRA site, so nothing is sent to JRA.
"""
import asyncio
import json
import os
import time
from urllib.parse import parse_qs

import pytest
from aiohttp import web

from k2kparser import aio, parser, calendar, result, video
from .conftest import FIXTURE_DIR, parse_fixture, _find_class


@pytest.fixture(autouse=True)
def fast_limits(monkeypatch):
    """ No interval / retry wait by default; restore the global limits after each test. """
    saved = aio.get_limits()
    aio.set_limits(max_concurrency=4, min_interval=0)
    monkeypatch.setattr(aio, 'RETRY_WAIT', 0)
    yield
    aio.set_limits(**saved)


async def start_server(handler):
    app = web.Application()
    app.router.add_route('*', '/{tail:.*}', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    return runner, 'http://127.0.0.1:{}'.format(port)


class Recorder:
    """ Handler that records concurrency and start times. """

    def __init__(self, delay=0.05, statuses=None):
        self.delay = delay
        self.statuses = list(statuses or [])
        self.active = 0
        self.max_active = 0
        self.starts = []

    async def handle(self, request):
        self.starts.append(time.monotonic())
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(self.delay)
            status = self.statuses.pop(0) if self.statuses else 200
            return web.Response(status=status, text='ok')
        finally:
            self.active -= 1


# ---- limits ----

@pytest.mark.parametrize('shared_client', [True, False])
def test_max_concurrency(shared_client):
    aio.set_limits(max_concurrency=2, min_interval=0)

    async def main():
        recorder = Recorder(delay=0.05)
        runner, base = await start_server(recorder.handle)
        try:
            if shared_client:
                async with aio.AsyncClient() as client:
                    await asyncio.gather(*(client.fetch(base + '/x{}'.format(i)) for i in range(8)))
            else:
                # Without a shared client the per-host limit still applies
                await asyncio.gather(*(aio.fetch(base + '/x{}'.format(i)) for i in range(8)))
        finally:
            await runner.cleanup()
        return recorder

    recorder = asyncio.run(main())
    assert len(recorder.starts) == 8
    assert recorder.max_active == 2


def test_min_interval():
    aio.set_limits(max_concurrency=4, min_interval=0.1)

    async def main():
        recorder = Recorder(delay=0)
        runner, base = await start_server(recorder.handle)
        try:
            async with aio.AsyncClient() as client:
                await asyncio.gather(*(client.fetch(base + '/x{}'.format(i)) for i in range(4)))
        finally:
            await runner.cleanup()
        return recorder

    starts = sorted(asyncio.run(main()).starts)
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    assert all(gap >= 0.09 for gap in gaps), gaps


def test_set_limits_validation():
    with pytest.raises(ValueError):
        aio.set_limits(max_concurrency=0)
    with pytest.raises(ValueError):
        aio.set_limits(min_interval=-1)


# ---- retry ----

@pytest.mark.parametrize('statuses, ok, requests', [
    ([503, 503], True, 3),          # retried, then succeeds
    ([503, 503, 503], False, 3),    # gives up after 3 tries
    ([404], False, 1),              # not retried
    ([429], True, 2),               # rate limited: retried
])
def test_retry(statuses, ok, requests):
    async def main():
        recorder = Recorder(delay=0, statuses=statuses)
        runner, base = await start_server(recorder.handle)
        try:
            async with aio.AsyncClient() as client:
                try:
                    await client.fetch(base + '/x')
                    return recorder, None
                except parser.ParseErrorHTTP as e:
                    return recorder, e
        finally:
            await runner.cleanup()

    recorder, error = asyncio.run(main())
    assert (error is None) == ok
    assert len(recorder.starts) == requests
    if error is not None:
        assert error.code == statuses[-1]


def test_connection_error():
    async def main():
        async with aio.AsyncClient(timeout=2) as client:
            await client.fetch('http://127.0.0.1:1/x')

    with pytest.raises(parser.ParseError):
        asyncio.run(main())


def test_client_must_be_open():
    with pytest.raises(RuntimeError):
        asyncio.run(aio.AsyncClient().fetch('http://127.0.0.1:1/x'))


# ---- aparse() returns the same as parse() ----

def _load(label):
    meta_path = os.path.join(FIXTURE_DIR, label + '.meta.json')
    if not os.path.exists(meta_path):
        pytest.skip('fixture not captured: ' + label)
    with open(meta_path, encoding='utf-8') as f:
        meta = json.load(f)
    with open(os.path.join(FIXTURE_DIR, label + '.html'), encoding='utf-8') as f:
        return meta, f.read()


@pytest.mark.parametrize('label', ['den_kaisai', 'den_race', 'odds_tierce', 'result_race', 'uma', 'search'])
def test_aparse_same_as_parse(label):
    meta, html = _load(label)
    cls = _find_class(meta['class'])
    cname = parse_qs(meta['param'])['cname'][0]
    received = {}

    async def handler(request):
        received['method'] = request.method
        received['form'] = dict(await request.post())
        body = html.encode('Shift_JISx0213')
        return web.Response(body=body, content_type='text/html')

    async def main():
        runner, base = await start_server(handler)
        try:
            path = meta['uri'].replace(parser.JRA_BASE_URL, '')
            if cls is parser.ParserPost or issubclass(cls, parser.ParserPost):
                p = cls.__new__(cls)
                parser.ParserPost.__init__(p, path, cname, base_url=base)
            async with aio.AsyncClient() as client:
                return await p.aparse(client)
        finally:
            await runner.cleanup()

    out = asyncio.run(main())
    assert received['method'] == 'POST'
    assert received['form'] == {'cname': cname}        # sent as a form, same as the sync parse()
    assert out == parse_fixture(label)


# ---- parsers that fetch more pages ----

def test_calendar_aparse_concurrent_and_ordered(monkeypatch):
    month_json = [{'data': [
        {'date': str(d), 'info': [{'race': [{'name': 'x'}]}]} for d in (22, 1, 7, 8, 14, 15, 21)
    ] + [{'date': '2', 'info': [{}]}]}]
    order = []

    async def afetch(self, client=None):
        return json.dumps(month_json)

    async def afetch_day(self, day, client=None):
        await asyncio.sleep(0.05 if day == 1 else 0)     # day 1 finishes last
        order.append(day)
        if day == 21:
            raise parser.ParseErrorHTTP(404)              # not published yet: stop here
        if day == 8:
            raise parser.ParseErrorHTTP(500)              # skipped
        return [{'day': day}]

    monkeypatch.setattr(calendar.ParserCalendar, 'afetch', afetch)
    monkeypatch.setattr(calendar.ParserCalendar, 'afetch_day', afetch_day)

    days = asyncio.run(calendar.ParserCalendar(year=2026, month=11).aparse())

    assert order[-1] == 1                                 # fetched concurrently
    assert [d['date'] for d in days] == ['2026-11-01', '2026-11-07', '2026-11-14', '2026-11-15']
    assert days[0] == {'date': '2026-11-01', 'weekday': '日', 'kaisai': [{'day': 1}]}


@pytest.mark.parametrize('fetch_video, expected_calls', [(False, 0), (True, 1)])
def test_result_race_aparse_fetch_video(monkeypatch, fetch_video, expected_calls):
    calls = []

    async def aparse(self, client=None):
        return {'videos': {'race': {'video_id': '202605080504', 'contract_company_no': 2}}}

    async def aresolve(videos, client=None):
        calls.append(videos)

    monkeypatch.setattr(parser.Parser, 'aparse', aparse)
    monkeypatch.setattr(video, 'aresolve_videos', aresolve)
    p = result.ParserResultRace('/JRADB/accessS.html', 'pw01sde0108202605050420261121/AE', fetch_video=fetch_video)
    asyncio.run(p.aparse())
    assert len(calls) == expected_calls


def test_aresolve_videos(monkeypatch):
    meta = 'metaDataResult({});'.format(json.dumps({'movie': {
        'duration': '126', 'movie_list_hls': [{'text': 'auto', 'url': 'jmc_pd/1/abc.m3u8'}]}}))
    master = '#EXTM3U\n#EXT-X-STREAM-INF:RESOLUTION=854x480\nabc.m3u8'
    base = video.cdn_base_url(2)
    responses = {base + video.META_PATH.format('202605080504'): meta, base + 'jmc_pd/1/abc.m3u8': master}

    async def fetch(url, data=None, client=None):
        if url not in responses:
            raise parser.ParseErrorHTTP(404)
        return responses[url].encode('utf-8')

    monkeypatch.setattr(aio, 'fetch', fetch)
    videos = {'race': {'video_id': '202605080504', 'contract_company_no': 2},
              'patrol': {'video_id': '202605080504a', 'contract_company_no': 2}}

    asyncio.run(video.aresolve_videos(videos))

    assert videos['race'] == {'video_id': '202605080504', 'contract_company_no': 2,
                              'master_url': base + 'jmc_pd/1/abc.m3u8', 'resolutions': ['854x480'],
                              'duration': 126}
    assert videos['patrol'] == {'video_id': '202605080504a', 'contract_company_no': 2}
