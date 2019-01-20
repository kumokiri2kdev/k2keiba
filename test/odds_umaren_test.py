import sys
import logging
sys.path.insert(0, '../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    races = [
        'pw154ou1006201805091120181228Z/F7',
        'pw154ou1006201805011120181201Z/80', # 取り消しあり 2018年 ステイヤーズステークス
        'pw154ou1008201805061120181118Z/5D', # 18頭立て 2018年 マイルチャンピオンシップ
        'pw154ou1005201805020920181104Z/BB', # 6頭立て 2018年11月4日（日曜） 5回東京2日 9R
    ]

    for race in races:
        pow = po.OddsParserBracket('/JRADB/accessO.html', race)
        odds = pow.parse()

        logger.info(odds)
