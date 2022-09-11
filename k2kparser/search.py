import logging
import urllib
import re

from . import util
from . import parser


logger = logging.getLogger(__name__)

class ParserSearch(parser.ParserPost):
    def __init__(self, path, param, key, category='all', **kwargs):
        if category == 'active':
            aditional = '0010'
        elif category == 'inactive':
            aditional = '0001'
        else:
            aditional = '0000'

        param = param + aditional +  urllib.parse.quote(key, encoding='Shift_JISx0213')
        super(ParserSearch, self).__init__(path, param, **kwargs)

    def parse_content(self, soup):
        """ Parse content and return array of uma info
            :param soup:
            :return: Array of uma info
                'active': 現役 : True, 抹消 : False
                'name': 馬名
                'param': URL and Post parameter
                'sex': 性別
                'age': 馬齢
                'trainer': 調教師
        """

        soup_tables = soup.find('table', attrs={'class': 'gray12'})

        if soup_tables is None:
            return []

        soup_tables = soup_tables.find_all('table')

        umas = []

        for i, soup_table in enumerate(soup_tables):
            soup_trs = soup_table.find_all('tr')
            for soup_tr in soup_trs:
                soup_tds = soup_tr.find_all('td')
                if soup_tds[0].getText() == '馬　名':
                    pass
                else:
                    uma = {}
                    soup_name = soup_tds[0]
                    name = soup_name.getText()
                    if name.startswith('*'):
                        uma['active'] = False
                    else:
                        uma['active'] = True

                    uma['name'] = name.replace('*', '')

                    soup_anchor = soup_name.find('a')
                    if soup_anchor.has_attr('onclick'):
                        try:
                            uma['link'] = util.Util.parse_func_params(soup_anchor['onclick'])
                        except parser.ParseError as per:
                            logger.info('Anchor parse error: ' + soup_anchor.getText())

                    sex_age = soup_tds[1].getText()
                    uma['age'] = re.sub(r'[^0-9]', '', sex_age)
                    uma['sex'] = re.sub(r'[0-9]', '', sex_age)
                    uma['trainer'] = soup_tds[2].getText()
                    area = soup_tds[3].getText().strip()
                    if area  != '':
                        if area == '美':
                            uma['trainer'] += '(美浦)'
                        elif area == '栗':
                            uma['trainer'] += '(栗東)'
                        else:
                            uma['trainer'] += '({})'.format(area)

                    umas.append(uma)


        return umas