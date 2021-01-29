""" JRA Tokubetsu Page Parser """
import logging
import re

from . import util
from . import parser


logger = logging.getLogger(__name__)

""" JRA Tokubetsu Top Page Parser """
class ParserTokubetuTop(parser.ParserPost):
    def parse_content(self, soup):

        ret = []

        soup_date_list = soup.find_all('div', attrs={'class': 'date_unit'})
        for soup_date in soup_date_list:
            ret_kaisai_list = []
            soup_date_tag = soup_date.find('h2')
            soup_rcs = soup_date.find_all('div', attrs={'class': 'rc'})
            for soup_rc in soup_rcs:
                soup_kaisai = soup_rc.find('h3')
                ret_races = []
                soup_links = soup_rc.find_all('li')
                for soup_link in soup_links:
                    soup_anchor = soup_link.find('a')
                    if soup_anchor is not None and soup_anchor.has_attr('onclick'):
                        try:
                            params = util.Util.parse_func_params(soup_anchor['onclick'])
                        except parser.ParseError as per:
                            logger.info('Anchor parse error: ' + soup_anchor.getText())

                    soup_span = soup_link.find('span', attrs={'class': 'opt'})
                    soup_class = soup_span.find('span', attrs={'class': 'class'})
                    soup_distance = soup_span.find('span', attrs={'class': 'dist'})
                    soup_cap = soup_span.find('span', attrs={'class': 'cap'})

                    soup_span.extract()

                    ret_races.append({
                        'name': soup_link.get_text(),
                        'class': soup_class.get_text(),
                        'course': soup_distance.get_text(),
                        'condition': soup_cap.get_text(),
                        'params': params
                    })
                ret_kaisai_list.append({
                    'kaisai': soup_kaisai.get_text(),
                    'races': ret_races

                })
            ret.append({
                'date': soup_date_tag.get_text(),
                'kaisai': ret_kaisai_list
            })

        return ret



""" JRA Tokubetsu Race Page Parser """
class ParserTokubetuRace(parser.ParserPost):
    def parse_content(self, soup):
        horses = []
        soup_horse_lists = soup.find_all('div', attrs={'class': 'horse_list'})
        for soup_horse_list in soup_horse_lists:
            soup_tables = soup_horse_list.find_all('table')
            for soup_table in soup_tables:
                soup_tbody = soup_table.find('tbody')
                soup_trs = soup_tbody.find_all('tr')
                for soup_tr in soup_trs:
                    soup_horse = soup_tr.find('td', attrs={'class': 'horse'})
                    soup_anchor = soup_horse.find('a')
                    if soup_anchor is not None and soup_anchor.has_attr('onclick'):
                        try:
                            params = util.Util.parse_func_params(soup_anchor['onclick'])
                        except parser.ParseError as per:
                            logger.info('Anchor parse error: ' + soup_anchor.getText())

                    soup_weight = soup_tr.find('td', attrs={'class': 'weight'})

                    horses.append({
                        'name': soup_horse.get_text(),
                        'url': params,
                        'hande': soup_weight.get_text()
                    })

        return horses
