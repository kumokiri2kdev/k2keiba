import sys
import logging
sys.path.append('../')

import k2kparser.odds as po


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    p = po.ParserOddsTop('/JRADB/accessD.html', 'pw15oli00/6D')
    kaisai_list = p.parse()

    for kaisai in kaisai_list:
        for day in kaisai['kaisai']:
            pk = po.ParserOddsKaisai(day['param']['url'], day['param']['param'])
            result = pk.parse()

            logger.info('日付 : '+ result['date'])
            logger.info(' {}回{}{}日'.format(result['index'], result['place'], result['nichisuu']))

            for race in result['races']:
                logger.info(' ' * 2 + '{}レース {}'.format(race['index'], race['name']))
                for key in race['odds_params'].keys():
                    logger.info('   {} {}'.format(key, race['odds_params'][key]))