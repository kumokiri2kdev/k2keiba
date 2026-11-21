""" JRA Calendar (開催日程) Parsers

Output keys follow docs/naming.md.
"""
from datetime import datetime
import logging
import re

from . import util
from . import parser
from .tokubetsu import WEIGHT_RULES

logger = logging.getLogger(__name__)


class ParserCalendarMonth(parser.Parser):
    """ 1開催日のレース一覧（開催日程のページ） """
    PATH = '/keiba/calendar{}/{}/{}/{:02d}{:02d}.html'

    def __init__(self, year, month, day, **kwargs):
        path = self.PATH.format(year, year, month, month, day)
        self.year = year
        self.month = month
        self.day = day

        super().__init__(path, **kwargs)

    @staticmethod
    def parse_race_cond(text, race):
        """ '（ダ）ハンデ' / '（芝）（牝）' -> surface, weight_rule, rule """
        text = util.Util.trim_clean(text)
        m = re.match(r'^（([^）]*)）', text)
        if m:
            surface = util.parse_surface(m.group(1))
            if surface:
                race['surface'] = surface
            text = text[m.end():].strip()
        for weight_rule in WEIGHT_RULES:
            if text.endswith(weight_rule):
                race['weight_rule'] = weight_rule
                text = text[:-len(weight_rule)].strip()
                break
        if text:
            race['rule'] = text

    def parse_content(self, soup):
        """
        :return: list of dict
            'kai', 'racecourse', 'nichi'
            'races': list of dict
                'race_num', 'name', 'class', 'distance', 'surface', 'rule', 'weight_rule', 'departure'
        """
        kaisais = []

        for soup_day in soup.find_all('table', attrs={'class': 'narrow-xy'}):
            kaisai = util.parse_kaisai_name(
                soup_day.find('caption').find('div', attrs={'class': 'main'}).get_text())
            kaisai['races'] = []

            for soup_tr in soup_day.find('tbody').find_all('tr'):
                race = {}

                soup_th = soup_tr.find('th')
                race_num = util.parse_int(soup_th.get_text())
                if race_num is not None:
                    race['race_num'] = race_num

                race_class = util.Util.trim_clean(soup_tr.find('p', attrs={'class': 'race_class'}).get_text())
                soup_stakes = soup_tr.find('p', attrs={'class': 'stakes'})
                race['name'] = util.Util.trim_clean(soup_stakes.get_text()) if soup_stakes else race_class
                race['class'] = race_class

                soup_cond = soup_tr.find('p', attrs={'class': 'race_cond'})
                race['distance'] = util.parse_int(soup_cond.find('span', attrs={'class': 'dist'}).get_text())
                self.parse_race_cond(soup_cond.find('span', attrs={'class': 'type'}).get_text(), race)

                departure = util.to_hhmm(soup_tr.find('td', attrs={'class': 'time'}).get_text())
                if departure:
                    race['departure'] = departure

                kaisai['races'].append(race)

            kaisais.append(kaisai)

        return kaisais


class ParserCalendar(parser.ParserJson):
    """ 1か月分の開催日程。開催日ごとに ParserCalendarMonth でページを取得する。 """
    PATH = '/keiba/common/calendar/json/{}.json?=_{}'

    def __init__(self, year=None, month=None, **kwargs):
        now = datetime.now(util.JST)
        self.year = year if year is not None else now.year
        self.month = month if month is not None else now.month

        calendar_id = '{}{:02d}'.format(self.year, self.month)
        super().__init__(self.PATH.format(calendar_id, int(now.timestamp())), **kwargs)

    def fetch_day(self, day):
        """ Fetch race list of one day. Overridable for tests. """
        return ParserCalendarMonth(self.year, self.month, day).parse()

    async def afetch_day(self, day, client=None):
        """ Asynchronous version of fetch_day(). Overridable for tests. """
        return await ParserCalendarMonth(self.year, self.month, day).aparse(client)

    @staticmethod
    def race_days(json_data):
        """ Days with races in the month JSON, in order. """
        days = []
        for date in sorted(json_data[0]['data'], key=lambda x: int(x['date'])):
            if 'race' in date['info'][0] and len(date['info'][0]['race']) > 0:
                days.append(int(date['date']))
        return days

    def build(self, results):
        """ [(day, kaisai list or ParseErrorHTTP)] in day order -> output.
        Stops at the first 404 (the page of that day and later is not published yet). """
        contents = []
        for day, kaisai in results:
            if isinstance(kaisai, parser.ParseErrorHTTP):
                if kaisai.code == 404:
                    break
                logger.warning('HTTP error {} : {}/{}/{}'.format(kaisai.code, self.year, self.month, day))
                continue

            date_obj = datetime(self.year, self.month, day)
            contents.append({'date': date_obj.strftime('%Y-%m-%d'),
                             'weekday': '月火水木金土日'[date_obj.weekday()],
                             'kaisai': kaisai})
        return contents

    def parse_content(self, json_data):
        """
        :return: list of dict（日付順）
            'date': 'YYYY-MM-DD'
            'weekday': '日'
            'kaisai': list of dict（ParserCalendarMonth の出力）
        """
        results = []
        for day in self.race_days(json_data):
            try:
                results.append((day, self.fetch_day(day)))
            except parser.ParseErrorHTTP as e:
                results.append((day, e))
                if e.code == 404:
                    break
        return self.build(results)

    async def aparse(self, client=None):
        """ Asynchronous version of parse(): the pages of the race days are fetched concurrently. """
        import asyncio
        import json

        json_data = json.loads(await self.afetch(client))
        days = self.race_days(json_data)

        async def fetch(day):
            try:
                return day, await self.afetch_day(day, client)
            except parser.ParseErrorHTTP as e:
                return day, e

        return self.build(await asyncio.gather(*(fetch(day) for day in days)))
