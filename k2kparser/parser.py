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
    _base_url = None

    @property
    def default_base_url(self):
        """ Base URL used when 'base_url' is not given. Override in subclasses. """
        return JRA_BASE_URL

    @property
    def base_url(self):
        if self._base_url is not None:
            return self._base_url
        return self.default_base_url

    @base_url.setter
    def base_url(self, value):
        self._base_url = value

    @property
    def decoder(self):
        return 'Shift_JISx0213'

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
            is_last = i >= HTTP_ERROR_RETRY - 1
            try :
                with urllib.request.urlopen(request) as response:
                    response_body = response.read().decode(self.decoder)
                break
            except urllib.error.HTTPError as e:
                if is_last:
                    logger.error('HTTP Error {} : {}'.format(e.code, self.uri))
                    raise ParseErrorHTTP(e.code)
                logger.info('HTTP Error {} Retry({})'.format(e.code, i + 1))
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if is_last:
                    logger.error('Connection Error {} : {}'.format(e, self.uri))
                    raise ParseError
                logger.info('Connection Error {} Retry({})'.format(e, i + 1))
            time.sleep(1)

        json_data = self.parse_html(response_body)

        return json_data

    async def aparse(self, client=None):
        """ Asynchronous version of parse() (asyncio + aiohttp).
        :param client: k2kparser.aio.AsyncClient to share connections between requests.
                       When None, a temporary client is used. Per-host limits apply either way.
        """
        body = await self.afetch(client)
        return self.parse_html(body)

    async def afetch(self, client=None):
        """ Fetch this page asynchronously and return the decoded body. """
        from . import aio     # aiohttp is needed only for the async API
        data = self.data if self.method == 'POST' else None
        body = await aio.fetch(self.uri, data=data, client=client)
        return body.decode(self.decoder)

    def parse_content(self, soup):
        logger.error("Base Class parse_content must not  be called")


class ParserJson(Parser):
    @property
    def decoder(self):
        return 'utf-8'

    def parse_html(self, content):
        json_data = json.loads(content)
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
        """ Parse the list of kaisai days.
        :return: list of dict
            'date': 'YYYY-MM-DD'
            'weekday': '土'
            'kaisai': list of dict
                'kai': 開催回, 'nichi': 開催日次, 'racecourse': 競馬場, 'link': link
            'win5_link': link (only on pages/days that have WIN5)
        """
        soup_days = self.parse_days(soup)
        kaisai_list = []

        for soup_day in soup_days:
            header = util.Util.trim_clean(soup_day.find('h3').getText())
            kaisai_info = {'date': util.to_iso_date(header)}
            weekday = util.parse_weekday(header)
            if weekday:
                kaisai_info['weekday'] = weekday
            kaisai_info['kaisai'] = []

            soup_kaisai_block = soup_day.find('div', attrs={'class': 'div3'})
            for soup_anchor in soup_kaisai_block.find_all('a'):
                kaisai_day = util.parse_kaisai_name(soup_anchor.getText().replace('馬番確定', ''))
                if 'kai' not in kaisai_day:
                    logger.info('parse_kaisai_name error: ' + soup_anchor.getText())
                    continue

                if soup_anchor.has_attr('onclick'):
                    try:
                        kaisai_day['link'] = util.Util.parse_func_params(soup_anchor['onclick'])
                    except ParseError:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())

                kaisai_info['kaisai'].append(kaisai_day)

            # The header has no year. Take it from a link parameter ('...20251004/45') when possible.
            for kaisai_day in kaisai_info['kaisai']:
                year = util.year_from_param(kaisai_day.get('link', {}).get('param', ''), kaisai_info['date'])
                if year is not None:
                    kaisai_info['date'] = util.to_iso_date(header, year=year)
                    break

            self.parse_addtionl_in_day(soup_day, kaisai_info)
            kaisai_list.append(kaisai_info)

        return kaisai_list
