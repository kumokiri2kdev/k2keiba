import sys
import logging
sys.path.append('../')

import k2kparser.den as pd
import k2kparser.win5 as pw

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pd.ParserDenTop('/JRADB/accessD.html', 'pw01dli00/F3')
    kaisai_list = p.parse()

    for kaisai in kaisai_list:
        if 'win5' in kaisai:
            url = kaisai['win5']
            while url is not None:
                logger.info('WIN5 : ' + url[1])
                p = pw.ParserWin5Kaisai(url[0], url[1])
                win5 = p.parse()
                logger.info(win5)
                url = win5['prev_url'] if 'prev_url' in win5 else None
