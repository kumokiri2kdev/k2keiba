import sys
import logging
sys.path.insert(0, '../')

import k2kparser.search as ps


def uma_search(key):
    p = ps.ParserSearch('/JRADB/accessR.html', 'pw02uliD1', key)
    uma_list = p.parse()

    logger.info('--- Key = {} ---'.format(key))

    for uma in uma_list:
        logger.info(uma)

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    uma_search('アイアン')
    uma_search('アイアンミ')

    uma_search('ロックディス')
