import sys
import logging
sys.path.insert(0, '../')

import k2kparser.den as pd
import k2kparser.win5 as pw

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pd.ParserDenTop('/JRADB/accessD.html', 'pw01dli00/F3')
    kaisai_list = p.parse()

    for kaisai in kaisai_list:
        if 'win5_link' in kaisai:
            link = kaisai['win5_link']
            while link is not None:
                logger.info('WIN5 : ' + link['param'])
                p = pw.ParserWin5Kaisai(link['url'], link['param'])
                win5 = p.parse()
                logger.info(win5)
                link = win5['prev_url'] if 'prev_url' in win5 else None
