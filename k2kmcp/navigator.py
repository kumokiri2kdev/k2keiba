""" Find JRA pages from (date, racecourse, race number) by walking the list pages.

Uses the async parsers (aparse), so the per-host limits of k2kparser.aio apply.
List pages are cached for a short time so that a series of tool calls does not fetch them again.
"""
import asyncio
import datetime
import re
import time

from k2kparser import den, odds, result, result_params, uma, search, kaisai, util, parser
from k2kparser.util import RACECOURSES

# Romanized names accepted as racecourse
RACECOURSE_ALIASES = {
    'sapporo': '札幌', 'hakodate': '函館', 'fukushima': '福島', 'niigata': '新潟', 'tokyo': '東京',
    'nakayama': '中山', 'chukyo': '中京', 'kyoto': '京都', 'hanshin': '阪神', 'kokura': '小倉',
}

ODDS_PARSERS = {
    'win': odds.OddsParserWin,                  # 単勝・複勝
    'wakuren': odds.OddsParserBracketQuinella,
    'umaren': odds.OddsParserBracket,
    'wide': odds.OddsParserWide,
    'umatan': odds.OddsParserExacta,
    'trio': odds.OddsParserTrio,
    'tierce': odds.OddsParserTierce,
}

# seconds
TTL_THIS_WEEK = 300
TTL_PAST = 24 * 3600
TTL_ODDS = 60


class NotFound(Exception):
    """ The requested meeting / race / horse does not exist (message is for the user). """


def normalize_racecourse(name):
    text = name.strip()
    if text in RACECOURSES:
        return text
    alias = RACECOURSE_ALIASES.get(text.lower())
    if alias:
        return alias
    for rc in RACECOURSES:              # '東京競馬場' etc.
        if rc in text:
            return rc
    raise NotFound('Unknown racecourse: {!r}. Use one of: {}'.format(name, ', '.join(RACECOURSES)))


def normalize_date(text):
    try:
        iso = util.to_iso_date(text)
        datetime.date.fromisoformat(iso)
        return iso
    except (util.UtilError, ValueError):
        raise NotFound('Invalid date: {!r}. Use YYYY-MM-DD.'.format(text))


def _is_fixed(link):
    """ Result pages: the 8th character of the parameter is '1' once the results are fixed
    ('pw01sde1...', 'pw01srl1...'); such pages do not change any more. """
    param = link.get('param', '')
    return len(param) > 7 and param[7] == '1'


def horse_id_of(link):
    """ {'param': 'pw01dud002022103614/A5'} -> '2022103614' """
    m = re.match(r'pw01dud[01]0(\d{10})/', (link or {}).get('param', ''))
    return m.group(1) if m else None


class Navigator:
    def __init__(self, client=None):
        self.client = client
        self._cache = {}
        self._locks = {}

    async def _get(self, key, ttl, make_parser):
        """ Parse a page with a small TTL cache (concurrent calls for the same page share one fetch). """
        hit = self._cache.get(key)
        if hit is not None and hit[0] > time.monotonic():
            return hit[1]
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            hit = self._cache.get(key)
            if hit is not None and hit[0] > time.monotonic():
                return hit[1]
            value = await make_parser().aparse(self.client)
            self._cache[key] = (time.monotonic() + ttl, value)
            return value

    async def _page(self, cls, link, ttl):
        return await self._get((cls.__name__, link['url'], link['param']), ttl,
                               lambda: cls(link['url'], link['param']))

    # ---- list pages ----

    async def den_days(self):
        return await self._get(('ParserDenTop',), TTL_THIS_WEEK, den.ParserDenTop)

    async def odds_days(self):
        return await self._get(('ParserOddsTop',), TTL_THIS_WEEK, odds.ParserOddsTop)

    async def result_days(self):
        return await self._get(('ParserResultTop',), TTL_THIS_WEEK, result.ParserResultTop)

    async def result_days_of_month(self, yyyymm):
        cname = result_params.ParserRaceParams.get_cname(yyyymm)
        ttl = TTL_THIS_WEEK if not result_params.ParserRaceParams.is_fixed(cname) else TTL_PAST
        return await self._get(('ParserResultKaisaiList', cname), ttl,
                               lambda: result.ParserResultKaisaiList('/JRADB/accessS.html', cname))

    async def track_conditions(self):
        return await self._get(('ParserKaisai',), TTL_THIS_WEEK, kaisai.ParserKaisai)

    # ---- meetings ----

    @staticmethod
    def _find_meeting(days, date, racecourse):
        """ -> kaisai entry, or None. Raises NotFound when the date is listed without that racecourse. """
        for day in days:
            if day['date'] != date:
                continue
            for meeting in day['kaisai']:
                if meeting.get('racecourse') == racecourse:
                    return meeting
            raise NotFound('No meeting at {} on {}. Meetings that day: {}'.format(
                racecourse, date, ', '.join(m.get('racecourse', '?') for m in day['kaisai'])))
        return None

    async def meeting(self, date, racecourse, kind):
        """ kaisai entry (with 'link') for kind = 'den' | 'odds' | 'result'. """
        date, racecourse = normalize_date(date), normalize_racecourse(racecourse)
        if kind == 'den':
            days = await self.den_days()
        elif kind == 'odds':
            days = await self.odds_days()
        else:
            days = await self.result_days()

        found = self._find_meeting(days, date, racecourse)
        if found is not None:
            return found

        if kind == 'result':
            # Not in this week's list: look in the month list (past results)
            yyyymm = int(date[:4] + date[5:7])
            try:
                month_days = await self.result_days_of_month(yyyymm)
            except parser.ParseError:
                month_days = []
            found = self._find_meeting(month_days, date, racecourse)
            if found is not None:
                return found
            raise NotFound('No race results for {} on {} (no meeting, or results are not published yet).'.format(
                racecourse, date))

        listed = ', '.join(d['date'] for d in days) or 'none'
        what = 'race cards' if kind == 'den' else 'odds'
        raise NotFound('JRA publishes {} only for this week. Dates available now: {}. '
                       'For past races use the race result tools.'.format(what, listed))

    # ---- races ----

    async def race_list(self, date, racecourse, kind):
        meeting = await self.meeting(date, racecourse, kind)
        cls = {'den': den.ParserDenKaisai, 'odds': odds.ParserOddsKaisai, 'result': result.ParserResultKaisai}[kind]
        ttl = TTL_PAST if _is_fixed(meeting['link']) else TTL_THIS_WEEK
        return await self._page(cls, meeting['link'], ttl)

    async def race_entry(self, date, racecourse, race_num, kind):
        races = await self.race_list(date, racecourse, kind)
        for race in races['races']:
            if race['race_num'] == race_num:
                return race
        raise NotFound('No race {}R at {} on {}. Races: {}'.format(
            race_num, normalize_racecourse(racecourse), normalize_date(date),
            ', '.join('{}R'.format(r['race_num']) for r in races['races'])))

    async def race_card(self, date, racecourse, race_num):
        race = await self.race_entry(date, racecourse, race_num, 'den')
        if 'link' not in race:
            raise NotFound('The race card of {}R is not available.'.format(race_num))
        return await self._page(den.ParserDenRace, race['link'], TTL_THIS_WEEK)

    async def race_result(self, date, racecourse, race_num, fetch_video=False):
        race = await self.race_entry(date, racecourse, race_num, 'result')
        if 'link' not in race:
            raise NotFound('The result of {}R is not published yet.'.format(race_num))
        link = race['link']
        if fetch_video:     # not cached: video links may be added later
            return await result.ParserResultRace(link['url'], link['param'], fetch_video=True).aparse(self.client)
        return await self._page(result.ParserResultRace, link, TTL_PAST if _is_fixed(link) else TTL_THIS_WEEK)

    async def odds(self, date, racecourse, race_num, bet_type):
        race = await self.race_entry(date, racecourse, race_num, 'odds')
        link = race.get('odds_links', {}).get(bet_type)
        if link is None:
            raise NotFound('No {} odds for {}R. Available: {}'.format(
                bet_type, race_num, ', '.join(race.get('odds_links', {})) or 'none'))
        return await self._page(ODDS_PARSERS[bet_type], link, TTL_ODDS)

    # ---- horses ----

    async def horse(self, horse_id):
        if not re.fullmatch(r'\d{10}', horse_id or ''):
            raise NotFound('Invalid horse_id: {!r} (10 digits, e.g. "2022103614").'.format(horse_id))
        param = util.make_param('pw01dud00' + horse_id)
        try:
            return await self._page(uma.ParserUma, {'url': '/JRADB/accessU.html', 'param': param}, TTL_THIS_WEEK)
        except parser.ParseErrorHTTP as e:
            raise NotFound('Horse {} not found (HTTP {}).'.format(horse_id, e.code))

    async def search_horses(self, name, status):
        p = search.ParserSearch('/JRADB/accessR.html', 'pw02uliD1', name, status)
        return await p.aparse(self.client)
