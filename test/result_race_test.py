import sys
import logging
sys.path.insert(0, '../')

import k2kparser.result as pr
import k2kparser.util as ut

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    races = [
        'pw01sde1009201805070620181222/EA', # メイクデビュー
        'pw01sde1009201805091020181228/52',
        'pw01sde1008201805061020181118/DA', # ７頭立て
        'pw01sde1009201805040920181209/27', # ７頭立て（８頭立て１頭除外)
        'pw01sde1006201805071020181222/20', # 中山大障害
        'pw01sde1007201804021120181202/FB', # チャンピオンズC
        'pw01sde1008201701010120170105/8A',  # 2017年1月5日 1回京都 1R(Issue#11)
        'pw01sde1006201805011120181201/B2',  # 2018年ステイヤーズステークス(Issue#12)
    ]

    for race in races:
        p = pr.ParserResultRace('/JRADB/accessS.html', race)
        race = p.parse()

        val = ut.Util.parse_date_to_int(race['date'])
        logger.info(val)
        logger.info(race)

