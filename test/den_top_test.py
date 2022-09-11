import sys
import logging
import pprint

sys.path.insert(0, '../')

import k2kparser.den as pd


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pd.ParserDenTop()
    kaisai_list = p.parse()

    logger.info(kaisai_list)
    pprint.pprint(kaisai_list)