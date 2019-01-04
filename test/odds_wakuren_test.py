import sys
import logging
sys.path.append('../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    races = [
        'pw153ou1006201805091120181228Z/73',
        'pw153ou1006201805011120181201Z/FC', # 取り消しあり 2018年 ステイヤーズステークス
        'pw153ou1008201805061120181118Z/D9', # 18頭立て 2018年 マイルチャンピオンシップ
    ]

    for race in races:
        pow = po.OddsParserBracketQuinella('/JRADB/accessO.html', race)
        odds = pow.parse()

        logger.info(odds)
