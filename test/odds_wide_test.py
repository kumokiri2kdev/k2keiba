import sys
import logging
sys.path.append('../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    races = [
        'pw155ou1006201805091120181228Z/7B',
        'pw155ou1006201805011120181201Z/04', # 取り消しあり 2018年 ステイヤーズステークス
        'pw155ou1008201805061120181118Z/E1', # 18頭立て 2018年 マイルチャンピオンシップ
        'pw155ou1005201805020920181104Z/3F', # 6頭立て 2018年11月4日（日曜） 5回東京2日 9R
    ]

    for race in races:
        pow = po.OddsParserWide('/JRADB/accessO.html', race)
        odds = pow.parse()

        logger.info(odds)