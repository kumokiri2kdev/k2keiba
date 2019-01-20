import sys
import logging
sys.path.insert(0, '../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    races = [
        'pw156ou1006201805091120181228Z/FF',
        'pw156ou1006201805011120181201Z/88', # 取り消しあり 2018年 ステイヤーズステークス
        'pw156ou1008201805061120181118Z/65', # 18頭立て 2018年 マイルチャンピオンシップ
        'pw156ou1005201805020920181104Z/C3', # 6頭立て 2018年11月4日（日曜） 5回東京2日 9R
    ]

    for race in races:
        pow = po.OddsParserExacta('/JRADB/accessO.html', race)
        odds = pow.parse()

        logger.info(odds)
