""" Parameters (CNAME) of the past race result pages (過去のレース結果検索)

The page of a month is opened with a CNAME like 'pw01skl10202510/1E'. JRA's "過去のレース結果検索"
page builds it in JavaScript:

    function setParameter(arg1, arg2){
      var yearMonth = "202611";                                                  // this month
      arg = arg1 + arg2;
      if(Number(arg) >= yearMonth){ param = 'pw01skl00' + String(arg) + '/'; }   // not fixed yet
      else                        { param = 'pw01skl10' + String(arg) + '/'; }   // fixed
      cname = param + objParam[String(arg).substring(2,6)];
      ...

The last 2 characters (objParam) are the checksum common to all JRA parameters, so they are
computed with util.param_checksum() instead of keeping the table.
"""
import datetime
import logging
import re

from . import parser
from . import util

logger = logging.getLogger(__name__)

# 「過去のレース結果検索」のページ
SEARCH_PATH = '/JRADB/accessS.html'
SEARCH_PARAM = 'pw01skl00999999/B3'

PREFIX_FIXED = 'pw01skl10'
PREFIX_NOT_FIXED = 'pw01skl00'


class ParserResultParams(parser.ParserPost):
    """ Read objParam / yearMonth from the JavaScript of the past result search page.
    Not needed to build CNAMEs; kept to check util.param_checksum() against JRA's own table. """

    def __init__(self, path=SEARCH_PATH, param=SEARCH_PARAM, **kwargs):
        super().__init__(path, param, **kwargs)

    def parse_content(self, soup):
        """
        :return: dict
            'year_month': int  (YYYYMM; this month and later use 'pw01skl00')
            'params': {'YYMM': 'XX'}  (e.g. {'2510': '1E'})
        :raises parser.ParseError: when the script is not found
        """
        script = '\n'.join(s.string or '' for s in soup.find_all('script'))
        params = dict(re.findall(r'objParam\[\s*"(\d{4})"\s*\]\s*=\s*"([0-9A-Fa-f]{2})"', script))
        year_month = re.search(r'var\s+yearMonth\s*=\s*"(\d{6})"', script)
        if not params or year_month is None:
            logger.error('objParam / yearMonth not found in the page')
            raise parser.ParseError
        return {'year_month': int(year_month.group(1)),
                'params': {k: v.upper() for k, v in params.items()}}


def this_month():
    """ Current YYYYMM in JST (yearMonth of JRA's script). """
    now = datetime.datetime.now(util.JST)
    return now.year * 100 + now.month


class ParserRaceParams:
    @classmethod
    def get_cname(cls, yyyymm, year_month=None):
        """ CNAME of the past result list of a month, for ParserResultKaisaiList.
        :param yyyymm: e.g. 202510
        :param year_month: months on or after this use 'pw01skl00' (default: this month)
        :return: 'pw01skl10202510/1E'
        """
        year_month = this_month() if year_month is None else year_month
        prefix = PREFIX_NOT_FIXED if yyyymm >= year_month else PREFIX_FIXED
        return util.make_param('{}{:06d}'.format(prefix, yyyymm))

    @classmethod
    def is_fixed(cls, param):
        return not param.startswith(PREFIX_NOT_FIXED)
