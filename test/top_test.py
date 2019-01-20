""" Test Code for ParserTop class. """
import sys
import logging
sys.path.insert(0, '../')

import k2kparser.top as pt

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pt.ParserTop()
    params = p.parse()

    list_to_be_checked = (
        'kaisai',
        'shutuba',
        'odds',
        'result',
        'haraimodoshi',
        'tokubetu'
    )

    for check_item in list_to_be_checked:
        if check_item in params:
            logger.info('{} exists : {}'.format(check_item, params[check_item]))
        else:
            logger.error('{} doesn\'t exist.'.format(check_item))
