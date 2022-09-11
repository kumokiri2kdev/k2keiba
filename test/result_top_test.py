import sys
import logging
import pprint
sys.path.insert(0, '../')

import k2kparser.result as pr


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pr.ParserResultTop()
    days = p.parse()

    for kaisai_list in days:
        logger.info(kaisai_list['date'])
        for kaisai in kaisai_list['kaisai']:
            logger.info(kaisai['link'])
            prk = pr.ParserResultKaisai(kaisai['link']['url'], kaisai['link']['param'])
            races = prk.parse()
            logger.info(races)
            for race in races['races']:
                logger.info('{}, {}'.format(race['link']['url'], race['link']['param']))
                prr = pr.ParserResultRace(race['link']['url'], race['link']['param'])
                race = prr.parse()
                pprint.pprint(race)
                #logger.info(race)


    logger.info(kaisai_list)
