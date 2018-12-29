""" JRA Den Page Top Parser """

from . import parser
from . import util

class ParserDenTop(parser.ParserPost):
    def __init__(self, path, param):
        super().__init__(path, param)
        self.kaisai_list = {}
        self.den_list = {'date_list': self.kaisai_list}

    def parse_content(self, soup):
        """ Parse content and return parameters if exist
        :param soup:
        :return: Array of Dict of Kaisai
            'date': 日付
            'kaisai': Array of Kaisai information
                'index': 開催回数
                'day': 開催日（何日目）
                'place': 競馬場
                'params': URL and Post parameter

        """
        soup_area = soup.find('div', attrs = {'id':'contentsBody'})
        soup_day_area = soup_area.find('div', attrs = {'id':'main'})
        soup_days = soup_day_area.find_all('div', attrs = {'class':'panel'})
        kaisai_list = []
        for soup_day in soup_days:
            kaisai_info = {}
            header = util.Util.trim_clean(soup_day.find('h3').getText())

            kaisai_info['date'] = header
            kaisai_info['kaisai'] = []

            soup_kaisai_list = soup_day.find_all('li', attrs = {'class':'waku'})
            for soup_kaisai in soup_kaisai_list:
                kaisai_info_day = {}
                soup_anchor = soup_kaisai.find('a')
                if soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                    except parser.ParseError as per:
                        pass

                try:
                    kaisai_param = util.Util.parse_kaisai(soup_kaisai.getText())
                except ValueError:
                    pass

                kaisai_info_day['index'] = kaisai_param[0]
                kaisai_info_day['day'] = kaisai_param[1]
                kaisai_info_day['place'] = kaisai_param[2]
                kaisai_info_day['param'] = util.Util.format_params(params)

                kaisai_info['kaisai'].append(kaisai_info_day)

            kaisai_list.append(kaisai_info)

        return kaisai_list
