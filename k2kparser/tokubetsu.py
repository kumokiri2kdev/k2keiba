""" JRA Tokubetsu (特別レース登録馬) Page Parsers

Output keys follow docs/naming.md.
"""
import logging

from . import util
from . import parser
from .den import _onclick_link, _href_link


logger = logging.getLogger(__name__)

WEIGHT_RULES = ('定量', '別定', '馬齢', 'ハンデ')


def split_condition(text):
    """ '（国際）（指定） 定量' -> {'rule': '（国際）（指定）', 'weight_rule': '定量'} """
    text = util.Util.trim_clean(text)
    ret = {}
    tokens = text.split()
    if tokens and tokens[-1] in WEIGHT_RULES:
        ret['weight_rule'] = tokens.pop()
    rule = ' '.join(tokens)
    if rule:
        ret['rule'] = rule
    return ret


class ParserTokubetuTop(parser.ParserPost):
    def parse_content(self, soup):
        """ 特別レース登録馬（レース一覧）
        :return: list of dict
            'date', 'weekday'
            'kaisai': list of dict
                'kai', 'racecourse', 'nichi'
                'races': list of dict
                    'name', 'grade', 'class', 'distance', 'surface', 'rule', 'weight_rule', 'link'
        """
        ret = []

        for soup_date in soup.find_all('div', attrs={'class': 'date_unit'}):
            header = soup_date.find('h2').get_text()
            day = {'date': util.to_iso_date(header)}
            weekday = util.parse_weekday(header)
            if weekday:
                day['weekday'] = weekday
            day['kaisai'] = []

            for soup_rc in soup_date.find_all('div', attrs={'class': 'rc'}):
                soup_kaisai = soup_rc.find('h3')
                if soup_kaisai is None:
                    continue

                kaisai = util.parse_kaisai_name(soup_kaisai.get_text())
                kaisai['races'] = []
                for soup_li in soup_rc.find_all('li'):
                    soup_anchor = soup_li.find('a')
                    if soup_anchor is None:
                        continue
                    race = {}
                    link = _onclick_link(soup_anchor)

                    soup_opt = soup_anchor.find('span', attrs={'class': 'opt'})
                    if soup_opt is not None:
                        soup_opt.extract()
                    soup_grade = soup_anchor.find('span', attrs={'class': 'grade_icon'})
                    if soup_grade is not None:
                        if soup_grade.find('img') is not None:
                            race['grade'] = soup_grade.find('img')['alt']
                        soup_grade.extract()
                    race['name'] = util.Util.trim_clean(soup_anchor.get_text())

                    if soup_opt is not None:
                        soup_class = soup_opt.find('span', attrs={'class': 'class'})
                        if soup_class is not None:
                            race['class'] = util.Util.trim_clean(soup_class.get_text())
                        soup_dist = soup_opt.find('span', attrs={'class': 'dist'})
                        if soup_dist is not None:
                            text = soup_dist.get_text()          # '2400メートル芝'
                            race['distance'] = util.parse_int(text)
                            surface = util.parse_surface(text)
                            if surface:
                                race['surface'] = surface
                        soup_cap = soup_opt.find('span', attrs={'class': 'cap'})
                        if soup_cap is not None:
                            race.update(split_condition(soup_cap.get_text()))

                    if link:
                        race['link'] = link
                    kaisai['races'].append(race)

                day['kaisai'].append(kaisai)

            ret.append(day)

        return ret


class ParserTokubetuRace(parser.ParserPost):
    def parse_content(self, soup):
        """ 特別レース登録馬（1レース）
        :return: list of dict
            'name', 'link', 'hande'
        """
        horses = []
        for soup_list in soup.find_all('div', attrs={'class': 'horse_list'}):
            for soup_table in soup_list.find_all('table'):
                soup_tbody = soup_table.find('tbody')
                if soup_tbody is None:
                    continue
                for soup_tr in soup_tbody.find_all('tr'):
                    soup_horse = soup_tr.find('td', attrs={'class': 'horse'})
                    if soup_horse is None:
                        continue
                    horse = {'name': util.Util.trim_clean(soup_horse.get_text())}
                    link = _href_link(soup_horse.find('a'))
                    if link:
                        horse['link'] = link
                    soup_weight = soup_tr.find('td', attrs={'class': 'weight'})
                    hande = util.parse_float(soup_weight.get_text()) if soup_weight else None
                    if hande is not None:
                        horse['hande'] = hande
                    horses.append(horse)

        return horses
