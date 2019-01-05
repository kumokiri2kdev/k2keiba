import sys
import logging
sys.path.append('../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    races = [
        'pw158ou1006201805091120181228Z/07',
        'pw158ou1006201805011120181201Z/90', # 取り消しあり 2018年 ステイヤーズステークス
        'pw158ou1008201805061120181118Z/6D', # 18頭立て 2018年 マイルチャンピオンシップ
        'pw158ou1005201805020920181104Z/CB', # 6頭立て 2018年11月4日（日曜） 5回東京2日 9R
    ]

    for race in races:
        pot = po.OddsParserTierce('/JRADB/accessO.html', race)
        odds = pot.parse()

        logger.info(odds)
