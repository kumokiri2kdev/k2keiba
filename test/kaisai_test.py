import sys
import logging
import pprint

sys.path.insert(0, '../')

import k2kparser.kaisai as pk

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pk.ParserKaisai()
    kaisai_info = p.parse()

    print(kaisai_info)





