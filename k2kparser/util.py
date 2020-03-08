""" Utilities for k2k_jra """
import re
import logging.config

from . import parser


logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'k2k_formatter': {
            'format': '[%(filename)s:%(lineno)03d] %(message)s'
        },
    },
    'handlers': {
        'k2k_handler': {
            'class': 'logging.StreamHandler',
            'formatter': 'k2k_formatter'
        }
    },
    'loggers': {
        'k2kparser': {
            'handlers': ['k2k_handler'],
            'level': logging.INFO,
            'propagate': 0
        }
    }
})

logger = logging.getLogger(__name__)

class UtilError(Exception):
    pass

class Util:
    @classmethod
    def parse_int_only(cls, str):
        try :
            num = int(re.sub(r'[^0-9]', '', str))
        except ValueError:
            raise UtilError

        return num

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
            place = re.sub(r'[0-9]回', '', str).lstrip('\n')
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

    @classmethod
    def parse_kaisai_date_week(cls, kaisai):
        kaisai = kaisai.strip()
        date = re.search(r'[0-9]{1,2}月[0-9]{1,2}日', kaisai)
        weekday = re.search(r'（[月火水木金土日]曜）', kaisai)

        return date[0], weekday[0].replace("（", "").replace("）", "")

    @classmethod
    def parse_course_distance(cls, str):
        course = re.sub(r'（|）', '', re.search(r'（.*）', str).group(0))
        distance = int(re.sub(r'[^0-9]', '', str.replace(course, '')))

        return distance, course

    @classmethod
    def parse_odds(cls, str):
        try:
            odds = float(re.search(r'.*[0-9]\(', str).group(0).replace('(',''))
            odds_rank = int(re.search(r'[0-9]+', re.search(r'\(.*\)', str).group(0)).group(0))
        except:
            raise ValueError

        return odds, odds_rank

    @classmethod
    def parse_weight(cls, str):
        try:
            str = Util.trim_clean(str)
            weight = int(re.search(r'[0-9]*', str).group(0))
            try:
                weight_diff = int(re.search(r'\(.*\)', str).group(0).replace('(','').replace(')',''))
            except:
                weight_diff = 0
        except:
            raise ValueError

        return weight, weight_diff

    @classmethod
    def parse_age(cls, str):
        str = Util.trim_clean(str)
        age = int(re.sub(r'[^0-9]', '', str))
        splits = (re.sub(r'[0-9]','', str).split('/'))

        if len(splits) > 1:
            return age, splits[0], splits[1]
        else:
            return age, splits[0]

    @classmethod
    def parser_date(cls, kaisai):
        kaisai = kaisai.strip()
        date = re.search(r'[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日', kaisai)
        weekday = re.search(r'（[月火水木金土日]）', kaisai)

        return date[0], weekday[0].replace("（", "").replace("）", "")

    @classmethod
    def parse_date_to_int(cls, date):
        int_val = 0

        int_val += int(re.search(r'[0-9]{4}年', date)[0].replace('年', '')) * 10000
        int_val += int(re.search(r'[0-9]{1,2}月', date)[0].replace('月', '')) * 100
        int_val += int(re.search(r'[0-9]{1,2}日', date)[0].replace('日', ''))

        return int_val

    @classmethod
    def parse_race_time(cls, time_str):
        try:
            time_str = cls.trim_clean(time_str)
            times = time_str.split(":")
            if len(times) > 1:
                time_sec = int(times[0]) * 600 + int(float(times[1]) * 10)
            else:
                time_sec = int(float(times[0]) * 10)
        except ValueError:
            logger.debug('Value error: {}'.format(time_str))
            raise UtilError

        return time_sec