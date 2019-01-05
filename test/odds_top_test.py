import sys
import logging
sys.path.append('../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = po.ParserOddsTop('/JRADB/accessD.html', 'pw15oli00/6D')
    kaisai_list = p.parse()

    logger.info(kaisai_list)