from logging import getLogger, INFO

import parser as pr

if __name__ == '__main__':
    logger = getLogger(__name__)
    logger.setLevel(INFO)

    p = pr.ParserDenTop('/JRADB/accessD.html', 'pw01dli00/F3')
    kaisai_list = p.parse()

    for kaisai in kaisai_list:
        for day in kaisai['kaisai']:
            pk = pr.ParserDenKaisai(day['param']['url'], day['param']['param'])
            result = pk.parse()

            logger.info('日付 : '+ result['date'])
            logger.info(' {}回{}{}日'.format(result['index'], result['place'], result['nichisuu']))

            for race in result['races']:
                logger.info(' ' * 2 + '{}レース {} : {}'.format(race['index'], race['name'], race['param']['param']))