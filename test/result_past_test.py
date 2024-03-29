import sys
import logging
sys.path.insert(0, '../')

import k2kparser.result as pr
import k2kparser.result_params as prp


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    current = 202212
    end = 202212

    while current <= end:
        param = prp.ParserRaceParams.get_cname(current)
        logger.info("Month : {}, Param : {}".format(current, param))

        prkl = pr.ParserResultKaisaiList('/JRADB/accessS.html', param)
        days = prkl.parse()
        logger.info(days)
        for day in days:
            for kaisai in day['kaisai']:
                logger.info(kaisai['link'])
                prk = pr.ParserResultKaisai(kaisai['link']['url'], kaisai['link']['param'])
                races = prk.parse()
                logger.info(races)
                for race in races['races']:
                    logger.info('{}, {}'.format(race['link']['url'], race['link']['param']))
                    prr = pr.ParserResultRace(race['link']['url'], race['link']['param'])
                    race = prr.parse()

                    logger.info(race)


        current += 1
        if (current % 100) % 13 == 0:
            current += 88
