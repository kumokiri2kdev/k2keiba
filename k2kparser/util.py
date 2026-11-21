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


JST = datetime.timezone(datetime.timedelta(hours=9))
RACECOURSES = ('東京', '中山', '京都', '阪神', '札幌', '函館', '新潟', '福島', '中京', '小倉')
_RACECOURSE_RE = '(' + '|'.join(RACECOURSES) + ')'


def to_iso_date(text, year=None):
    """ '2026年11月21日' / '11月21日' / '2026.11.21' / '2026/11/21' -> '2026-11-21'
    When the text has no year, `year` (default: this year in JST) is used. """
    m = re.search(r'(\d{4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})', text)
    if m:
        y, mo, d = (int(v) for v in m.groups())
    else:
        m = re.search(r'(\d{1,2})月\s*(\d{1,2})日', text)
        if not m:
            raise UtilError('date not found: {}'.format(text))
        y = year if year is not None else datetime.datetime.now(JST).year
        mo, d = (int(v) for v in m.groups())
    return '{:04d}-{:02d}-{:02d}'.format(y, mo, d)


def year_from_param(param, iso_date):
    """ Find the year of `iso_date` ('YYYY-MM-DD', year may be a guess) in a JRA parameter that
    embeds 'YYYYMMDD' (e.g. 'pw01srl10052025040120251004/45'). Returns None if not found. """
    mmdd = iso_date[5:7] + iso_date[8:10]
    m = re.search(r'(\d{4})' + mmdd + r'(?=/|Z|$)', param.split('/')[0] + '/')
    return int(m.group(1)) if m else None


def param_checksum(head):
    """ Last 2 characters of a JRA CNAME parameter ('pw01skl10202510' -> '1E').
    Weighted byte sum over head + '/', weight 33 * (p XOR (p >> 4)) for position p, plus 144, mod 256.
    (Found from ~1,100 parameters taken from JRA pages; see test_util.py.) """
    total = 144
    for p, ch in enumerate(head + '/'):
        total += 33 * (p ^ (p >> 4)) * ord(ch)
    return '{:02X}'.format(total % 256)


def make_param(head):
    """ 'pw01skl10202510' -> 'pw01skl10202510/1E' """
    return '{}/{}'.format(head, param_checksum(head))


def parse_weekday(text):
    """ '（土曜）' / '（土）' / '土曜日' -> '土'. Returns None if not found. """
    m = re.search(r'([月火水木金土日])曜', text) or re.search(r'（([月火水木金土日])）', text)
    return m.group(1) if m else None


def to_hhmm(text):
    """ '15時40分' / '15:40' -> '15:40'. Returns None if not found. """
    m = re.search(r'(\d{1,2})\s*[時:：]\s*(\d{1,2})', text)
    if not m:
        return None
    return '{:02d}:{:02d}'.format(int(m.group(1)), int(m.group(2)))


def parse_kaisai_name(text):
    """ '5回東京8日' -> {'kai': 5, 'racecourse': '東京', 'nichi': 8}. Missing parts are omitted. """
    m = re.search(r'(\d+)\s*回\s*' + _RACECOURSE_RE + r'\s*(\d+)\s*日', text)
    if m:
        return {'kai': int(m.group(1)), 'racecourse': m.group(2), 'nichi': int(m.group(3))}

    ret = {}
    m = re.search(r'(\d+)\s*回', text)
    if m:
        ret['kai'] = int(m.group(1))
    m = re.search(_RACECOURSE_RE, text)
    if m:
        ret['racecourse'] = m.group(1)
    return ret


def parse_surface(text):
    """ Normalize course text to '芝' / 'ダート' / '障害'. Returns None if unknown. """
    if '障' in text:
        return '障害'
    if 'ダ' in text:
        return 'ダート'
    if '芝' in text:
        return '芝'
    return None


def parse_int(text):
    """ '1,234円' -> 1234. Returns None when no digit is found. """
    digits = re.sub(r'[^0-9\-]', '', text)
    if digits in ('', '-'):
        return None
    return int(digits)


def parse_float(text):
    """ '57.0kg' -> 57.0. Returns None when not a number (e.g. '取消'). """
    m = re.search(r'-?\d+(\.\d+)?', text.replace(',', ''))
    return float(m.group(0)) if m else None


def parse_kaisai_header(text):
    """ '2026年11月21日（土曜） 5回京都5日' -> dict(date, weekday, kai, racecourse, nichi) """
    ret = {'date': to_iso_date(text)}
    weekday = parse_weekday(text)
    if weekday:
        ret['weekday'] = weekday
    # Strip the date part so that '21日' is not taken as nichi
    rest = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '', text)
    ret.update(parse_kaisai_name(rest))
    return ret


def person(name, link=None):
    """ Common shape for jockey / trainer: {'name', 'link', 'affiliation'}.
    A trailing '(栗東)' / '（美浦）' in the name is moved to 'affiliation'. """
    name = name.strip()
    ret = {}
    m = re.match(r'^(.*?)\s*[(（](美浦|栗東|地方|外国)[)）]$', name)
    if m:
        ret['name'] = m.group(1)
        ret['affiliation'] = m.group(2)
    else:
        ret['name'] = name
    if link is not None:
        ret['link'] = link
    return ret


def normalize_coat(text):
    """ '黒鹿毛' -> '黒鹿' (same notation as 出馬表) """
    text = text.strip()
    return text[:-1] if text.endswith('毛') and len(text) > 1 else text


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

        head = param.split('/')[0]
        return make_param(head[:7] + '10' + head[9:])

    @classmethod
    def is_past_result_parameter(cls, param):
        if param[7] == '0' and param[8] == '1':
            return True

        return False

    @classmethod
    def convert_horse_param_as_past(cls, param):
        if param[7] == '1':
            return param

        head = param.split('/')[0]
        return make_param(head[:7] + '10' + head[9:])

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
                time_sec = int(times[0]) * 600 + round(float(times[1]) * 10)
            else:
                time_sec = round(float(times[0]) * 10)
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



