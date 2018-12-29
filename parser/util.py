""" Utilities for k2k_jra """
import re

from . import parser


class Util:
    @classmethod
    def parse_func_params(cls, str):
        matched = re.search(r'\(.*\)', str)
        if matched:
            params = re.sub(r'[\(\)\']','', matched.group(0)).split(',')
            if len(params) > 1:
                return params
            else:
                raise parser.ParseError
        else:
            raise parser.ParseError

    @classmethod
    def trim_clean(cls, str):
        rt = str.replace('\n','').strip()
        return rt

    @classmethod
    def parse_kaisai(cls, str):
        try:
            searched = re.search(r'[0-9]回', str)
            kaisuu = int(re.sub(r'回', '', searched[0]))
            searched = re.search(r'[0-9]日', str)
            nichisuu = int(re.sub(r'日', '', searched[0]))
            place = re.sub(r'[0-9]回', '', str)
            place = re.sub(r'[0-9]日', '', place).split('\n')[0]

        except:
            raise ValueError

        return kaisuu, nichisuu, place

    @classmethod
    def format_params(cls, params):
        return {'url': params[0], 'param': params[1]}

    @classmethod
    def parse_kaisai_date(cls, kaisai):
        kaisai = kaisai.strip()
        date = re.search(r'[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日', kaisai)
        weekday = re.search(r'（[月火水木金土日]曜）', kaisai)
        kaisuu = re.search(r'[0-9]*回', kaisai)
        day = re.search(r'[0-9]*日$', kaisai)
        place = re.search(r'(東京|中山|京都|阪神|札幌|函館|新潟|福島|中京|小倉)', kaisai)

        return date[0], weekday[0].replace("（", "").replace("）", ""), int(kaisuu[0].replace("回", "")), \
               place[0], int(day[0].replace("日", ""))
