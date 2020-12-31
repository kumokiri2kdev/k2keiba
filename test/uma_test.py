import sys
import logging
sys.path.insert(0, '../')

import pprint

import k2kparser.uma as pu


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    umas = [
        'pw01dud102014105926/A0', # シンギュラリティ
        'pw01dud102010102446/CE', # サウンドトゥルー
        'pw01dud102013106101/1C', # サトノダイヤモンド
        'pw01dud102014190002/8E', # パヴェル
        'pw01dud002015104107/21',
        'pw01dud102016105439/2C'
    ]

    for uma in umas:
        p = pu.ParserUma('/JRADB/accessU.html', uma)
        uma_info = p.parse()

        logger.info(uma_info)
        pprint.pprint(uma_info)
