import sys
import logging
sys.path.append('../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    races = [
        'pw157ou1006201805091120181228Z99/E5',
        'pw157ou1006201805011120181201Z99/6E', # 取り消しあり 2018年 ステイヤーズステークス
        'pw157ou1008201805061120181118Z99/4B', # 18頭立て 2018年 マイルチャンピオンシップ
        'pw157ou1005201805020920181104Z99/A9', # 6頭立て 2018年11月4日（日曜） 5回東京2日 9R
    ]

    for race in races:
        pot = po.OddsParserTrio('/JRADB/accessO.html', race)
        odds = pot.parse()

        logger.info(odds)
