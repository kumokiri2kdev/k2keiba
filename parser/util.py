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

