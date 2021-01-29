import sys
import logging
sys.path.insert(0, '../')

import k2kparser.tokubetsu as pt

import pprint


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pt.ParserTokubetuTop('/JRADB/accessT.html', 'pw03trl00/29')
    kaisai_list = p.parse()

    pprint.pprint(kaisai_list)

    for date in kaisai_list:
        for kaisai in date['kaisai']:
            for race in kaisai['races']:
                rp = pt.ParserTokubetuRace(race['params'][0],race['params'][1])
                horse_list = rp.parse()
                pprint.pprint(horse_list)
