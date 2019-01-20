import sys
import logging
sys.path.insert(0, '../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    races = [
        'pw151ou1006201805091120181228Z/6B',
        'pw151ou1006201805011120181201Z/F4', # 取り消しあり 2018年 ステイヤーズステークス
        'pw151ou1008201805061120181118Z/D1', # 18頭立て 2018年 マイルチャンピオンシップ
        'pw151ou1005201805020920181104Z/2F', # 6頭立て 2018年11月4日（日曜） 5回東京2日 9R
    ]

    for race in races:
        pow = po.OddsParserWin('/JRADB/accessO.html', race)
        odds = pow.parse()

        logger.info(odds)
