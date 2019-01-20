""" Test Code for ParserTop class. """
import sys
import logging
sys.path.insert(0, '../')

import k2kparser.parser as pr
import k2kparser.top as pt

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    try :
        p = pt.ParserTop()
        params = p.parse()
    except pr.ParseError:
        logger.error('k2kparser.ParseError')
        exit(1)

    for item in params:
        logger.info('{} : {}'.format(item['tag'], item['params']))
