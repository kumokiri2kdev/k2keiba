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
            logger.info(' {}回{}{}日'.format(result['index'], result['place'], result['nichisuu']))
            if 'weather' in result:
                logger.info(' 天候 : {}, 芝 : {}, ダート : {}'.format(result['weather'], result['turf'], result['dirt']))

            for race in result['races']:
                logger.info(' ' * 2 + '{}レース {} : {}'.format(race['index'], race['name'], race['link']['param']))

            pprint.pprint(result)

        if 'win5' in kaisai:
            logger.info('WIN5 : ' + kaisai['win5'][1])

