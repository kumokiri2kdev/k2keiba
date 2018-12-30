""" Test Code for ParserTop class. """
from logging import getLogger, INFO

import parser as pr


if __name__ == '__main__':
    logger = getLogger(__name__)
    logger.setLevel(INFO)

    p = pr.ParserTop()
    params = p.parse()

    list_to_be_checked = (
        'kaisai',
        'shutuba',
        'odds',
        'haraimodoshi',
        'tokubetu'
    )

    for check_item in list_to_be_checked:
        if check_item in params:
            logger.info('{} exists : {}'.format(check_item, params[check_item]))
        else:
            logger.error('{} doesn\'t exist.'.format(check_item))
