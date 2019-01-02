""" JRA Result Page Parser """
import logging

from . import util
from . import parser

logger = logging.getLogger(__name__)


class ParserResultTop(parser.ParserPost):

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

            soup_links = soup_day.find('ul', attrs={'class': 'link_list'})
            soup_kaisai_list = soup_links.find_all('li')
            for soup_kaisai in soup_kaisai_list:
                kaisai_info_day = {}
                soup_anchor = soup_kaisai.find('a')
                if soup_anchor is None:
                    break

                if soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())

                try:
                    kaisai_param = util.Util.parse_kaisai(soup_kaisai.getText())
                except ValueError:
                    logger.info('parse_kaisai error: ' + soup_kaisai.getText())

                kaisai_info_day['index'] = kaisai_param[0]
                kaisai_info_day['day'] = kaisai_param[1]
                kaisai_info_day['place'] = kaisai_param[2]
                kaisai_info_day['param'] = util.Util.format_params(params)

                kaisai_info['kaisai'].append(kaisai_info_day)

            kaisai_list.append(kaisai_info)

            soup_win5 = soup_day.find('ul', attrs={'class': 'win5'})
            soup_anchor = soup_win5.find('a')
            if soup_anchor is not None:
                if soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                        kaisai_info['win5'] = params
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())


        return kaisai_list

