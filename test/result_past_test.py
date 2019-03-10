import sys
import logging
sys.path.insert(0, '../')

import k2kparser.result as pr
import k2kparser.result_params as prp


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    current = 201902
    end = 201903

    while current <= end:
        param = prp.ParserRaceParams.get_cname(current)
        logger.info("Month : {}, Param : {}".format(current, param))

        prkl = pr.ParserResultKaisaiList('/JRADB/accessS.html', param)
        days = prkl.parse()
        logger.info(days)
        for day in days:
            for kaisai in day['kaisai']:
                logger.info(kaisai['param'])
                prk = pr.ParserResultKaisai(kaisai['param']['url'], kaisai['param']['param'])
                races = prk.parse()
                logger.info(races)
                for race in races['races']:
                    logger.info('{}, {}'.format(race['param']['url'], race['param']['param']))
                    prr = pr.ParserResultRace(race['param']['url'], race['param']['param'])
                    race = prr.parse()

                    logger.info(race)


        current += 1
        if (current % 100) % 13 == 0:
            current += 88
