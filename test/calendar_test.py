import sys
import logging
sys.path.insert(0, '../')

import pprint

import k2kparser.calendar as pc


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    for i in range(1, 13):
        p = pc.ParserCalendar(year=2021, month=i)
        kaisais = p.parse()
        if len(kaisais) < 1:
            break

        pprint.pprint(kaisais)
