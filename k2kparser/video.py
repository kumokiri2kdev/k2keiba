""" JRA race replay video (レース映像・全周パトロール)

Result pages embed the replay buttons as
    <script>eqPlayerButtonByAccount('202605080504', 2);</script>     レース映像
    <script>eqPlayerButtonByAccount('202605080504a', 2);</script>    全周パトロール
Past result pages use the older form
    <script>eqPlayerButton('202203040503');</script>
The video id is resolved to an HLS master playlist through the streaming CDN metadata.

The "contract company number" selects the CDN account (see eqOnetag.js / eqPcPlayer*.html of JRA):
    eqPlayerButtonByAccount(id, contract_company_no, default_low)
    eqPlayerButton(id, default_low, contract_company_no)     contract_company_no defaults to 1

Output keys follow docs/naming.md.
"""
import json
import logging
import re
import urllib.error
import urllib.request
from urllib.parse import urljoin

from . import parser

logger = logging.getLogger(__name__)

# 契約会社番号 -> CDN のアカウント
CDN_ACCOUNTS = {
    1: 'eqd109zrse',     # eqPcPlayer.html  (past races)
    2: 'eqc834rezx',     # eqPcPlayer2.html (recent races)
}
DEFAULT_CONTRACT_COMPANY_NO = 1
CDN_BASE_URL = 'https://{0}.eq.webcdn.stream.ne.jp/www50/{0}/jmc_pub/'
META_PATH = 'eq_meta/v1_o/{}.jsonp'
TIMEOUT = 15

_BUTTON_RE = re.compile(
    r"""eqPlayerButton(ByAccount)?\(\s*['"]([0-9]{12}[a-z]?)['"]\s*((?:,\s*[^,)]*)*)\)""")

# 動画 ID の末尾 -> 種類
VIDEO_KINDS = {'': 'race', 'a': 'patrol'}


class VideoError(parser.ParseError):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


def cdn_base_url(contract_company_no):
    try:
        return CDN_BASE_URL.format(CDN_ACCOUNTS[contract_company_no])
    except KeyError:
        raise VideoError('unknown contract company number: {}'.format(contract_company_no))


def _contract_company_no(by_account, args):
    """ Contract company number from the button arguments (after the id). """
    args = [a.strip().strip('\'"') for a in args.split(',')[1:]]   # leading ',' gives an empty first item
    position = 0 if by_account else 1
    if len(args) > position and args[position].isdigit():
        return int(args[position])
    return DEFAULT_CONTRACT_COMPANY_NO


def parse_video_ids(soup):
    """ Find replay buttons in a page.
    :return: {'race': {'video_id', 'contract_company_no'}, 'patrol': {...}}
             Buttons not (yet) on the page are omitted.
    """
    videos = {}
    for soup_script in soup.find_all('script'):
        text = soup_script.string or ''
        for by_account, video_id, args in _BUTTON_RE.findall(text):
            kind = VIDEO_KINDS.get(video_id[12:])
            if kind is None:
                logger.info('Unknown video id: ' + video_id)
                continue
            videos.setdefault(kind, {'video_id': video_id,
                                     'contract_company_no': _contract_company_no(by_account, args)})
    return videos


def _fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'K2Keiba'})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.read().decode('utf-8-sig')
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise VideoError('fetch failed: {} ({})'.format(url, e))


def get_hls(video_id, contract_company_no=DEFAULT_CONTRACT_COMPANY_NO):
    """ Resolve a video id to its HLS master playlist (2 requests to the CDN).
    :param contract_company_no: from parse_video_ids() (1: past races, 2: recent races)
    :return: dict
        'master_url': HLS マスタープレイリストの URL
        'resolutions': ['480x270', '640x360', '854x480']
        'duration': 長さ（秒）
    :raises VideoError: when the video is not available (yet) or the response is unexpected
    """
    meta_url = _meta_url(video_id, contract_company_no)
    movie, master_url = _parse_metadata(video_id, contract_company_no, _fetch(meta_url))
    return _hls_info(movie, master_url, _fetch(master_url))


async def aget_hls(video_id, contract_company_no=DEFAULT_CONTRACT_COMPANY_NO, client=None):
    """ Asynchronous version of get_hls(). `client`: k2kparser.aio.AsyncClient (optional). """
    meta_url = _meta_url(video_id, contract_company_no)
    movie, master_url = _parse_metadata(video_id, contract_company_no, await _afetch(meta_url, client))
    return _hls_info(movie, master_url, await _afetch(master_url, client))


async def _afetch(url, client):
    from . import aio
    try:
        body = await aio.fetch(url, client=client)
    except parser.ParseErrorHTTP as e:
        raise VideoError('fetch failed: {} (HTTP {})'.format(url, e.code))
    except VideoError:
        raise
    except parser.ParseError:
        raise VideoError('fetch failed: {}'.format(url))
    return body.decode('utf-8-sig')


def _meta_url(video_id, contract_company_no):
    return urljoin(cdn_base_url(contract_company_no), META_PATH.format(video_id))


def _parse_metadata(video_id, contract_company_no, metadata):
    """ -> (movie dict, master playlist URL) """
    wrapper = re.fullmatch(r'\s*metaDataResult\((.*)\)\s*;?\s*', metadata, re.S)
    if not wrapper:
        raise VideoError('unexpected metadata format: ' + video_id)
    try:
        movie = json.loads(wrapper.group(1))['movie']
        master = next((s['url'] for s in movie['movie_list_hls'] if s.get('text') == 'auto'), None)
    except (ValueError, KeyError, TypeError) as e:
        raise VideoError('unexpected metadata: {} ({!r})'.format(video_id, e))
    if not master:
        raise VideoError('master playlist not found: ' + video_id)
    return movie, urljoin(cdn_base_url(contract_company_no), master)


def _hls_info(movie, master_url, manifest):
    manifest = manifest.splitlines()
    variants = [line for line in manifest if line.startswith('#EXT-X-STREAM-INF:')]
    if not manifest or manifest[0].strip() != '#EXTM3U' or not variants:
        raise VideoError('invalid master playlist: ' + master_url)

    ret = {
        'master_url': master_url,
        'resolutions': list(dict.fromkeys(re.findall(r'\bRESOLUTION=([0-9]+x[0-9]+)', '\n'.join(variants)))),
    }
    try:
        ret['duration'] = int(movie['duration'])     # seconds; given as a string ('126')
    except (KeyError, TypeError, ValueError):
        pass
    return ret


def resolve_videos(videos):
    """ Add HLS info (get_hls) to each entry of parse_video_ids() output, in place.
    A video that cannot be resolved keeps only its id (logged as warning). """
    for kind, video in videos.items():
        try:
            video.update(get_hls(video['video_id'],
                                 video.get('contract_company_no', DEFAULT_CONTRACT_COMPANY_NO)))
        except VideoError as e:
            logger.warning('HLS not available for {} ({}): {}'.format(kind, video['video_id'], e))
    return videos


async def aresolve_videos(videos, client=None):
    """ Asynchronous version of resolve_videos(): all videos are resolved concurrently. """
    import asyncio

    async def resolve(kind, video):
        try:
            video.update(await aget_hls(video['video_id'],
                                        video.get('contract_company_no', DEFAULT_CONTRACT_COMPANY_NO), client))
        except VideoError as e:
            logger.warning('HLS not available for {} ({}): {}'.format(kind, video['video_id'], e))

    await asyncio.gather(*(resolve(kind, video) for kind, video in videos.items()))
    return videos
