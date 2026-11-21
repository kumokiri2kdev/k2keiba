""" Asynchronous fetching for k2kparser (asyncio + aiohttp)

    import asyncio
    from k2kparser import aio, den

    async def main():
        async with aio.AsyncClient() as client:
            days = await den.ParserDenTop().aparse(client)
            kaisais = await asyncio.gather(*(
                den.ParserDenKaisai(k['link']['url'], k['link']['param']).aparse(client)
                for day in days for k in day['kaisai']))

    asyncio.run(main())

Requests are always throttled per host, however aparse() is called (with or without a shared
client): at most `max_concurrency` requests are in flight and request starts are at least
`min_interval` seconds apart. Change the limits with set_limits().
"""
import asyncio
import logging
import weakref
from urllib.parse import urlsplit

import aiohttp

from . import parser

logger = logging.getLogger(__name__)

USER_AGENT = 'K2Keiba'
DEFAULT_MAX_CONCURRENCY = 4
DEFAULT_MIN_INTERVAL = 0.25     # seconds between request starts (per host)
DEFAULT_TIMEOUT = 15            # seconds per request
RETRY_WAIT = 1.0                # seconds before retrying a failed request

_limits = {'max_concurrency': DEFAULT_MAX_CONCURRENCY, 'min_interval': DEFAULT_MIN_INTERVAL}
# event loop -> {host: _HostLimiter}
_limiters = weakref.WeakKeyDictionary()


def set_limits(max_concurrency=DEFAULT_MAX_CONCURRENCY, min_interval=DEFAULT_MIN_INTERVAL):
    """ Change the per-host limits. Applies to limiters created after this call
    (call it before starting requests). """
    if max_concurrency < 1:
        raise ValueError('max_concurrency must be >= 1')
    if min_interval < 0:
        raise ValueError('min_interval must be >= 0')
    _limits['max_concurrency'] = max_concurrency
    _limits['min_interval'] = min_interval
    _limiters.clear()


def get_limits():
    return dict(_limits)


class _HostLimiter:
    """ At most `max_concurrency` holders at a time, and holders start `min_interval` apart. """

    def __init__(self, max_concurrency, min_interval):
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._lock = asyncio.Lock()
        self._min_interval = min_interval
        self._next_start = 0.0

    async def __aenter__(self):
        await self._semaphore.acquire()
        try:
            async with self._lock:
                loop = asyncio.get_running_loop()
                wait = self._next_start - loop.time()
                if wait > 0:
                    await asyncio.sleep(wait)
                self._next_start = loop.time() + self._min_interval
        except BaseException:
            self._semaphore.release()
            raise
        return self

    async def __aexit__(self, *exc):
        self._semaphore.release()


def _limiter_for(url):
    loop = asyncio.get_running_loop()
    host = urlsplit(url).netloc
    per_loop = _limiters.setdefault(loop, {})
    if host not in per_loop:
        per_loop[host] = _HostLimiter(_limits['max_concurrency'], _limits['min_interval'])
    return per_loop[host]


def _retryable(status):
    """ 5xx and 408/429 may succeed later; other 4xx (e.g. 404) will not. """
    return status >= 500 or status in (408, 429)


class AsyncClient:
    """ Shared HTTP session for aparse(). Use as `async with AsyncClient() as client:`.
    Sharing one client reuses connections; the per-host limits apply either way. """

    def __init__(self, timeout=DEFAULT_TIMEOUT, retry=parser.HTTP_ERROR_RETRY):
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._retry = retry
        self._session = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(timeout=self._timeout, headers={'User-Agent': USER_AGENT})
        return self

    async def __aexit__(self, *exc):
        await self.close()

    async def close(self):
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def fetch(self, url, data=None):
        """ GET (or POST when `data` is given) and return the body as bytes.
        :raises parser.ParseErrorHTTP: HTTP error after retries
        :raises parser.ParseError: connection error / timeout after retries
        """
        if self._session is None:
            raise RuntimeError('AsyncClient is not open (use "async with AsyncClient() as client")')

        method = 'POST' if data is not None else 'GET'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'} if data is not None else None
        limiter = _limiter_for(url)

        for i in range(self._retry):
            is_last = i >= self._retry - 1
            try:
                async with limiter:
                    async with self._session.request(method, url, data=data, headers=headers) as response:
                        if response.status >= 400:
                            raise parser.ParseErrorHTTP(response.status)
                        return await response.read()
            except parser.ParseErrorHTTP as e:
                if is_last or not _retryable(e.code):
                    logger.log(logging.ERROR if _retryable(e.code) else logging.INFO,
                               'HTTP Error {} : {}'.format(e.code, url))
                    raise
                logger.info('HTTP Error {} Retry({})'.format(e.code, i + 1))
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if is_last:
                    logger.error('Connection Error {!r} : {}'.format(e, url))
                    raise parser.ParseError
                logger.info('Connection Error {!r} Retry({})'.format(e, i + 1))
            await asyncio.sleep(RETRY_WAIT)     # outside the limiter: do not hold a slot while waiting


async def fetch(url, data=None, client=None):
    """ Fetch with `client`, or with a temporary client when None. """
    if client is not None:
        return await client.fetch(url, data)
    async with AsyncClient() as temporary:
        return await temporary.fetch(url, data)
