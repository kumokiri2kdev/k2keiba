import sys
import logging
sys.path.insert(0, '../')

import k2kparser.den as pd
import k2kparser.win5 as pw

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pw.ParserWin5Kaisai('/JRADB/access5.html', 'pw17hde01202502021/D7')
    win5 = p.parse()
    logger.info(win5)
                
    