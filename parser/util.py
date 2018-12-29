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