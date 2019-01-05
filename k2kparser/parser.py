""" Parser Base Class """
import logging
import urllib.request
from abc import ABCMeta, abstractmethod

from bs4 import BeautifulSoup

from . import util


JRA_BASE_URL = 'http://www.jra.go.jp'


logger = logging.getLogger(__name__)

class ParseError(Exception):
	def __init__(self):
		pass

class Parser:
    def __init__(self, file_path, **kwargs):
        self.uri = self.gen_asb_uri(file_path)

        if 'data' in kwargs:
            self.method = 'POST'
            self.data = kwargs['data'].encode('utf-8')
        else:
            self.method = 'GET'

    def gen_asb_uri(self, file_path):
        return JRA_BASE_URL + file_path

    def parse_html(self, content):
        soup = BeautifulSoup(content, "html.parser")
        return self.parse_content(soup)

    def parse(self):
        if self.method == 'POST':
            request = urllib.request.Request(self.uri, data=self.data, method='POST')
        else:
            request = urllib.request.Request(self.uri)

        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("'Shift_JISx0213'")

        return self.parse_html(response_body)

    def parse_content(self, soup):
        logger.error("Base Class parse_content must not  be called")


class ParserPost(Parser):
    def __init__(self, path, param):
        param = 'cname=' + param
        super(ParserPost,self).__init__(path, data=param)


class ParserKaisaiTop(ParserPost, metaclass=ABCMeta):
    @abstractmethod
    def get_base_soup(self, soup):
        pass

    def parse_addtionl_in_day(self, soup_day, kaisai_info):
        pass

    def parse_content(self, soup):
        soup_thisweek = self.get_base_soup(soup)
        soup_days = soup_thisweek.find_all('div', attrs={'class': 'panel'})
        kaisai_list = []

        for soup_day in soup_days:
            kaisai_info = {}
            header = util.Util.trim_clean(soup_day.find('h3').getText())

            kaisai_info['date'] = header
            kaisai_info['kaisai'] = []

            soup_div3 = soup_day.find('ul', attrs={'class': 'div3'})
            soup_kaisai_list = soup_div3.find_all('li')
            for soup_kaisai in soup_kaisai_list:
                kaisai_info_day = {}
                soup_anchor = soup_kaisai.find('a')
                if soup_anchor is None:
                    continue

                if soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                    except ParseError as per:
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

            self.parse_addtionl_in_day(soup_day, kaisai_info)

        return kaisai_list
