""" JRA Search (競走馬検索) Page Parser

Output keys follow docs/naming.md.
"""
import logging
import urllib.parse
import re

from . import util
from . import parser
from .den import _onclick_link, _href_link


logger = logging.getLogger(__name__)


class ParserSearch(parser.ParserPost):
    def __init__(self, path, param, key, category='all', **kwargs):
        if category == 'active':
            aditional = '0010'
        elif category == 'inactive':
            aditional = '0001'
        else:
            aditional = '0000'

        param = param + aditional + urllib.parse.quote(key, encoding='Shift_JISx0213')
        super(ParserSearch, self).__init__(path, param, **kwargs)

    def parse_content(self, soup):
        """ 検索結果
        :return: list of dict
            'active': 現役なら True、抹消なら False
            'name': 馬名
            'link': 馬ページ
            'sex': 性別
            'age': 馬齢（抹消馬は抹消時）
            'trainer': {'name', 'link', 'affiliation'}
        """
        umas = []

        soup_body = soup.find('div', attrs={'id': 'contentsBody'}) or soup
        for soup_table in soup_body.find_all('table'):
            soup_head = soup_table.find('thead')
            if soup_head is None or soup_head.find('th', attrs={'class': 'horse'}) is None:
                continue

            for soup_tr in soup_table.find('tbody').find_all('tr'):
                soup_horse = soup_tr.find('td', attrs={'class': 'horse'})
                if soup_horse is None:
                    continue
                uma = {}

                soup_icon = soup_horse.find('span', attrs={'class': 'icon'})
                uma['active'] = soup_icon is None or '抹' not in soup_icon.get_text()
                if soup_icon is not None:
                    soup_icon.extract()

                uma['name'] = util.Util.trim_clean(soup_horse.get_text())
                link = _href_link(soup_horse.find('a')) or _onclick_link(soup_horse.find('a'))
                if link:
                    uma['link'] = link

                sex_age = util.Util.trim_clean(soup_tr.find('td', attrs={'class': 'age'}).get_text())
                age = util.parse_int(sex_age)
                if age is not None:
                    uma['age'] = age
                uma['sex'] = re.sub(r'[0-9]', '', sex_age)

                soup_trainer = soup_tr.find('td', attrs={'class': 'trainer'})
                if soup_trainer is not None:
                    soup_area = soup_trainer.find('span', attrs={'class': 'right'})
                    area = util.Util.trim_clean(soup_area.get_text()) if soup_area else ''
                    if soup_area is not None:
                        soup_area.extract()
                    trainer = util.person(util.Util.trim_clean(soup_trainer.get_text()),
                                          _onclick_link(soup_trainer.find('a')))
                    if area:
                        trainer['affiliation'] = area
                    if trainer['name']:
                        uma['trainer'] = trainer

                umas.append(uma)

        return umas
