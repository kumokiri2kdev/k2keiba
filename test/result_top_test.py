import sys
import logging
sys.path.append('../')

import k2kparser.result as pr


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pr.ParserResultTop('/JRADB/accessS.html', 'pw01sli00/AF')
    kaisai_list = p.parse()

    logger.info(kaisai_list)