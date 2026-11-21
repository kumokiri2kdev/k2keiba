import sys
import logging
import pprint

sys.path.insert(0, '../')

import k2kparser.den as pd


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = pd.ParserDenTop()
    kaisai_list = p.parse()

    for kaisai in kaisai_list:
        for day in kaisai['kaisai']:
            pk = pd.ParserDenKaisai(day['link']['url'], day['link']['param'])
            result = pk.parse()

            logger.info('日付 : '+ result['date'])
            logger.info(' {}回{}{}日'.format(result['kai'], result['racecourse'], result['nichi']))
            if 'weather' in result:
                logger.info(' 天候 : {}, 馬場 : {}'.format(result['weather'], result.get('track_condition')))

            for race in result['races']:
                logger.info(' ' * 2 + '{}レース {} : {}'.format(race['race_num'], race['name'], race['link']['param']))

            pprint.pprint(result)

        if 'win5_link' in kaisai:
            logger.info('WIN5 : ' + kaisai['win5_link']['param'])

