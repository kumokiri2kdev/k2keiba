""" JRA Kaisai Page Parser """
import logging
import re

from . import util
from . import parser

logger = logging.getLogger(__name__)


class ParserKaisai(parser.ParserPost):

    def __init__(self, path='/JRADB/accessI.html', param='pw01ide01/4F'):
        super().__init__(path, param)


    def parse_header(self, soup):
        header_soup = soup.find('div', attrs={'class': 'contents_header'})
        main_soup = header_soup.find('div', attrs={'class': 'main'})
        main_soup_text = main_soup.get_text().strip('\n')
        ret = {
            'date': main_soup_text.split('\u3000')[0]
        }

        return ret

    def parse_weather(self, soup):
        weather_block_soup = soup.find('div', attrs={'class': 'weather_block'})
        thead_soup = weather_block_soup.find('thead')
        rcs_soup = thead_soup.find_all('th', attrs={'class': 'rc'})

        ret = []
        for rc_soup in rcs_soup:
            ret.append({
                'place': rc_soup.get_text().strip()
            })

        tbody_soup = weather_block_soup.find('tbody')
        weather_soup = tbody_soup.find('tr', attrs={'class': 'weather'})
        weather_list_soup = weather_soup.find_all('div', attrs={'class' : 'weather'})

        for i, weather_info_soup in enumerate(weather_list_soup):
            ret[i]['weather'] = weather_info_soup.get_text()

        baba_soup = tbody_soup.find('tr', attrs={'class': 'baba'})
        baba_uls_soup = baba_soup.find_all('ul')

        for i, baba_ul_soup in enumerate(baba_uls_soup):
            caps_soup = baba_ul_soup.find_all('span', attrs={'class': 'cap'})

            ret[i]['condition'] = {}
            for cap_soup in caps_soup:
                if 'turf' in cap_soup['class']:
                    ret[i]['condition']['turf'] = cap_soup.parent.find('span', attrs={'class': 'main'}).get_text()
                elif 'dirt' in cap_soup['class']:
                    ret[i]['condition']['dirt'] = cap_soup.parent.find('span', attrs={'class': 'main'}).get_text()

        return ret

    def parse_content(self, soup):
        ret = {}
        kaisai_info_soup = soup.find('div', attrs={'class': 'kaisai_info_unit'})
        if kaisai_info_soup is None:
            return ret

        date = self.parse_header(kaisai_info_soup)
        ret.update(date)

        weather = self.parse_weather(kaisai_info_soup)
        ret['places'] = weather

        return ret
