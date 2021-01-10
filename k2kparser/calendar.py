""" JRA Result Page Parser """
from datetime import datetime, timedelta, timezone
import urllib.request
import urllib.error

import logging
import pprint

from . import util
from . import parser

logger = logging.getLogger(__name__)

# class ParserCalendarMonth(parser.Parser):
#     PATH = '/keiba/calendar/{}'
#
#     def __init__(self, path):
#         super().__init__(ParserCalendar.PATH.format(path))
#
#     def parse_content(self, soup):
#         print(soup)

class ParserCalendarMonth(parser.Parser):
    PATH = '/keiba/calendar{}/{}/{}/{:02d}{:02d}.html'
    def __init__(self, year, month, day):
        path = self.PATH.format(year, year, month, month, day)
        self.year = year
        self.month = month
        self.day = day

        super().__init__(path)

    def parse_content(self, soup):
        soup_days = soup.find_all('table', attrs={'class': 'narrow-xy'})

        kaisais = []

        for soup_day in soup_days:
            soup_caption = soup_day.find('caption')
            soup_kaisai = soup_caption.find('div', attrs={'class': 'main'})
            kaisai = soup_kaisai.get_text()
            soup_trs = soup_day.find('tbody').find_all('tr')
            races = []
            for soup_tr in soup_trs:
                race = {}

                soup_th = soup_tr.find('th')
                assert soup_th is not None
                soup_th.find('span').decompose()
                try :
                    race_no = int(soup_th.get_text())
                except :
                    race_no = soup_th.get_text()

                #print(race_no)
                race['index'] = race_no

                soup_class = soup_tr.find('p', attrs={'class': 'race_class'})
                race_class = soup_class.get_text()
                #print(race_class)
                race['class'] = race_class

                soup_stakes = soup_tr.find('p', attrs={'class': 'stakes'})
                if soup_stakes is not None:
                    race_name = soup_stakes.get_text()
                else:
                    race_name = race_class
                #print(race_name)
                race['name'] = race_name

                soup_cond = soup_tr.find('p', attrs={'class': 'race_cond'})
                soup_dist = soup_cond.find('span', attrs={'class': 'dist'})
                soup_type = soup_cond.find('span', attrs={'class': 'type'})

                distance = soup_dist.get_text()
                type = soup_type.get_text()

                #print(distance)
                race['distance'] = distance

                #print(type)
                type = type.split('）')
                course = type[0].replace('（','')
                cond = type[1]
                race['course'] = course
                race['cond'] = cond

                soup_time = soup_tr.find('td', attrs={'class': 'time'})
                departure = soup_time.get_text()
                #print(departure)
                race['departure'] = departure

                races.append(race)

            kaisais.append({
                'kaisai': kaisai,
                'races': races
            })

        return kaisais



class ParserCalendar(parser.ParserJson):
    PATH = '/keiba/common/calendar/json/{}.json?=_{}'

    def __init__(self, year=None, month=None):
        JST = timezone(timedelta(hours=+9), 'JST')

        now = datetime.now(JST)

        if year is None:
            year = now.year

        if month is None:
            month = now.month

        calendar_id ='{}{:02d}'.format(year, month)

        ts = int(now.timestamp())


        self.year = year
        self.month = month

        print(self.PATH.format(calendar_id, ts))
        super().__init__(self.PATH.format(calendar_id, ts))


    def parse_content(self, json_data):
        contents = []
        for date in sorted(json_data[0]['data'], key=lambda x: int(x['date'])):
            if 'race' in date['info'][0] and len(date['info'][0]['race']) > 0:
                #pprint.pprint(date)
                #print('{}/{}'.format(self.year, self.month))
                day = int(date['date'])
                pm = ParserCalendarMonth(self.year, self.month, day)
                try :
                    races = pm.parse()
                    #pprint.pprint(races)
                    contents.append({
                        'year': self.year,
                        'month': self.month,
                        'day': day,
                        'races': races
                    })
                except parser.ParseErrorHTTP as e:
                    if e.code == 404:
                        break
                    print(e.code)


        return contents