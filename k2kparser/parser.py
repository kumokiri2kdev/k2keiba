""" Parser Base Class """
import os
import json
import logging
import urllib.request
import urllib.error
from abc import ABCMeta, abstractmethod
import time

from bs4 import BeautifulSoup

from . import util


JRA_BASE_URL = 'https://www.jra.go.jp'
HTTP_ERROR_RETRY = 3

logger = logging.getLogger(__name__)

class ParseError(BaseException):
	def __init__(self):
		pass

class ParseErrorHTTP(ParseError):
    def __init__(self, code):
        self.code = code

class Parser:
    @property
    def base_url(self):
        return JRA_BASE_URL

    @property
    def decoder(self):
        return "'Shift_JISx0213'"

    def __init__(self, file_path, **kwargs):
        if 'data' in kwargs:
            self.method = 'POST'
            self.data = kwargs['data'].encode('utf-8')
        else:
            self.method = 'GET'

        if 'base_url' in kwargs:
            self.base_url = kwargs['base_url']
        #else:
            #if 'K2K_JRA_BASE_URL' in os.environ:
            #    self.base_url = os.environ['K2K_JRA_BASE_URL']
            #else:
            #    self.base_url = JRA_BASE_URL

        self.uri = self.gen_asb_uri(file_path)

    def gen_asb_uri(self, file_path):
        return self.base_url + file_path

    def parse_html(self, content):
        soup = BeautifulSoup(content, "html.parser")
        return self.parse_content(soup)

    def parse(self):
        headers = {
            'User-Agent': 'K2Keiba'
            #'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'
        }
        if self.method == 'POST':
            request = urllib.request.Request(self.uri, data=self.data, method='POST', headers=headers)
        else:
            request = urllib.request.Request(self.uri, headers=headers)

        for i in range(HTTP_ERROR_RETRY):
            try :
                with urllib.request.urlopen(request) as response:
                    response_body = response.read().decode(self.decoder)
            except urllib.error.HTTPError as e:
                if i > HTTP_ERROR_RETRY:
                    raise ParseErrorHTTP(e.code)
                else:
                    logger.info('HTTP Error Retry({})'.format(i + 1))
                    time.sleep(1)

        json_data = self.parse_html(response_body)

        return json_data

    def parse_content(self, soup):
        logger.error("Base Class parse_content must not  be called")


class ParserJson(Parser):
    @property
    def decoder(self):
        return "'utf-8'"

    def parse_html(self, content):
        json_data = json.loads(content, encoding=self.decoder)
        return self.parse_content(json_data)


class ParserPost(Parser):
    def __init__(self, path, param, **kwargs):
        param = 'cname=' + param.replace('/', '%2F')
        #param = urllib.parse.quote(param).replace('/', '%2F')
        super(ParserPost,self).__init__(path, data=param, **kwargs)


class ParserKaisaiTop(ParserPost, metaclass=ABCMeta):
    @abstractmethod
    def get_base_soup(self, soup):
        pass

    def parse_addtionl_in_day(self, soup_day, kaisai_info):
        pass

    def parse_days(self, soup):
        soup_thisweek = self.get_base_soup(soup)
        soup_days = soup_thisweek.find_all('div', attrs={'class': 'panel'})

        return soup_days

    def parse_content(self, soup):
        soup_days = self.parse_days(soup)
        kaisai_list = []

        for soup_day in soup_days:
            kaisai_info = {}
            header = util.Util.trim_clean(soup_day.find('h3').getText())
            date, weekday = util.Util.parse_kaisai_date_week(header)

            kaisai_info['date'] = date
            kaisai_info['week_day'] = weekday
            kaisai_info['kaisai'] = []

            soup_kaisai_block = soup_day.find('div', attrs={'class': 'div3'})
            soup_anchors = soup_kaisai_block.find_all('a')
            for soup_anchor in soup_anchors:
                kaisai_info_day = {}

                if soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                    except ParseError as per:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())

                try:
                    kaisai_text = soup_anchor.getText().replace('馬番確定','')
                    kaisai_param = util.Util.parse_kaisai(kaisai_text)
                except ValueError:
                    logger.info('parse_kaisai error: ' + soup_anchor.getText())

                kaisai_info_day['index'] = kaisai_param[0]
                kaisai_info_day['day'] = kaisai_param[1]
                kaisai_info_day['place'] = kaisai_param[2]
                kaisai_info_day['link'] = params

                kaisai_info['kaisai'].append(kaisai_info_day)

            kaisai_list.append(kaisai_info)

            self.parse_addtionl_in_day(soup_day, kaisai_info)

        return kaisai_list
