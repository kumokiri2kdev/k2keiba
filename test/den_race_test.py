import sys
import logging
import json
sys.path.insert(0, '../')

import k2kparser.den as pd


def print_race(race):
    json_data = json.dumps(race, indent=2,
                           ensure_ascii=False)
    logger.info(json_data)

if __name__ == '__main__':
    logging.config.fileConfig('logging.ini',disable_existing_loggers=False )
    logger = logging.getLogger(__name__)

    args = sys.argv

    if len(args) < 3:
        p = pd.ParserDenTop()
        kaisai_list = p.parse()

        for kaisai in kaisai_list:
            for day in kaisai['kaisai']:
                pk = pd.ParserDenKaisai(day['param']['url'], day['param']['param'])
                result = pk.parse()

                for race in result['races']:
                    pr = pd.ParserDenRace('/JRADB/accessD.html', race['param']['param'])
                    race = pr.parse()
                    print_race(race)

    else:
        pd = pd.ParserDenRace('/JRADB/accessD.html', args[1])
        race = pd.parse()
        print_race(race)
