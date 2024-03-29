""" Utilities for k2k_jra """
import re
import logging.config
import datetime

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
            params = [param.strip() for param in params]
            if len(params) > 1:
                return Util.format_params(params)
            else:
                raise parser.ParseError
        else:
            raise parser.ParseError

    @classmethod
    def convert_resul_param_as_past(cls, param):
        if param[7] == '1':
            return param

        param_list = list(param)
        param_list[7] = '1'
        param_list[8] = '0'
        param = ''.join(param_list)
        params = param.split('/')
        tail = '{:02X}'.format((int(params[-1], 16) + 0xff - 0x20) & 0x00ff)

        return '{}/{}'.format(params[0], tail)

    @classmethod
    def is_past_result_parameter(cls, param):
        if param[7] == '0' and param[8] == '1':
            return True

        return False

    @classmethod
    def convert_horse_param_as_past(cls, param):
        if param[7] == '1':
            return param

        param_list = list(param)
        param_list[7] = '1'
        param_list[8] = '0'
        param = ''.join(param_list)
        params = param.split('/')
        tail = '{:02X}'.format((int(params[-1], 16) + 0xff - 0x18) & 0x00ff)

        return '{}/{}'.format(params[0], tail)

    @classmethod
    def is_past_horse_parameter(cls, param):
        if param[7] == '1' and param[8] == '0':
            return True

        return False

    @classmethod
    def encode_slash(cls, param):
        return param.replace('/', '%2F')

    @classmethod
    def decode_slash(cls, param):
        return param.replace('%2F', '/')

    @classmethod
    def trim_clean(cls, str):
        rt = str.replace('\n','').strip()
        return rt

    @classmethod
    def parse_kaisai(cls, str):
        try:
            searched = re.search(r'[0-9]*回', str)
            kaisuu = int(re.sub(r'回', '', searched[0]))
            searched = re.search(r'[0-9]*日', str)
            nichisuu = int(re.sub(r'日', '', searched[0]))
            place = re.sub(r'[0-9]*回', '', str).lstrip('\n')
            place = re.sub(r'[0-9]*日', '', place).split('\n')[0]

        except:
            raise ValueError

        return kaisuu, nichisuu, place

    @classmethod
    def format_params(cls, params):
        return {'url': params[0], 'param': params[1]}

    @classmethod
    def format_params2(cls, params):
        segs = params.split('?')
        param = segs[1].split('=')
        return {'url': segs[0], 'param': param[1]}

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
    def parse_date_mmdd(cls, date):
        kaisai = date.strip()
        date = re.search(r'[0-9]{1,2}月[0-9]{1,2}日', kaisai)

        return date[0]


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
        if weekday is None:
            weekday = re.search(r'（[月火水木金土日]曜）', kaisai)

        return date[0], weekday[0].replace("（", "").replace("）", "")

    @classmethod
    def parse_date_to_int(cls, date):
        int_val = 0

        int_val += int(re.search(r'[0-9]{4}年', date)[0].replace('年', '')) * 10000
        int_val += int(re.search(r'[0-9]{1,2}月', date)[0].replace('月', '')) * 100
        int_val += int(re.search(r'[0-9]{1,2}日', date)[0].replace('日', ''))

        return int_val

    @classmethod
    def parse_date_to_datetime(cls, date):
        year = int(re.search(r'[0-9]{4}年', date)[0].replace('年', ''))
        month = int(re.search(r'[0-9]{1,2}月', date)[0].replace('月', ''))
        day = int(re.search(r'[0-9]{1,2}日', date)[0].replace('日', ''))

        date = datetime.date(year, month, day)

        return date

    @classmethod
    def parse_date_mmdd_to_datetime(cls, date):
        date = date.strip()
        year = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        ).year
        month = int(re.search(r'[0-9]{1,2}月', date)[0].replace('月', ''))
        day = int(re.search(r'[0-9]{1,2}日', date)[0].replace('日', ''))

        date = datetime.date(year, month, day)

        return date

    @classmethod
    def parse_date_mmdd_to_int(cls, date, year=None):
        if year is None:
            year = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=9))
            ).year

        int_val = year * 10000
        int_val += int(re.search(r'[0-9]{1,2}月', date)[0].replace('月', '')) * 100
        int_val += int(re.search(r'[0-9]{1,2}日', date)[0].replace('日', ''))

        return int_val

    @classmethod
    def parse_int_to_datetime(cls, date):
        year = int(date / 10000)
        date %= 10000
        month = int(date / 100)
        day = date % 100

        date = datetime.date(year, month, day)

        return date


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

    @classmethod
    def parse_timestr_to_datetime(clscls, time_str, date=None):
        if date is None:
            date = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=9))
            ).date()
        hour_segs = re.search(r'[0-9]{1,2}時', time_str)
        if hour_segs is None:
            return None
        hour = int(hour_segs[0].replace('時', ''))

        minute_seg = re.search(r'[0-9]{1,2}分', time_str)
        if minute_seg is None:
            return None
        minute = int(minute_seg[0].replace('分', ''))

        return datetime.datetime(year=date.year, month=date.month, day=date.day, hour=hour, minute=minute)



