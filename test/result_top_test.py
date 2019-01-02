import sys
import logging
sys.path.append('../')

import k2kparser.result as pr


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pr.ParserResultTop('/JRADB/accessS.html', 'pw01sli00/AF')
    days = p.parse()
    for kaisai_list in days:
        logger.info(kaisai_list['date'])
        for kaisai in kaisai_list['kaisai']:
            logger.info(kaisai['param'])
            prk = pr.ParserResultKaisai(kaisai['param']['url'], kaisai['param']['param'])
            races = prk.parse()
            logger.info(races)
            for race in races['races']:
                logger.info('{}, {}'.format(race['param']['url'], race['param']['param']))
                prr = pr.ParserResultRace(race['param']['url'], race['param']['param'])
                race = prr.parse()

                logger.info(race)


    logger.info(kaisai_list)
