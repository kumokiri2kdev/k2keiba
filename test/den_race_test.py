from logging import getLogger, INFO
import sys
import json

import parser as pr

def print_race(race):
    json_data = json.dumps(race, indent=2,
                           ensure_ascii=False)
    logger.info(json_data)

if __name__ == '__main__':
    logger = getLogger(__name__)
    logger.setLevel(INFO)

    args = sys.argv

    if len(args) < 2:
        p = pr.ParserDenTop('/JRADB/accessD.html', 'pw01dli00/F3')
        kaisai_list = p.parse()

        for kaisai in kaisai_list:
            for day in kaisai['kaisai']:
                pk = pr.ParserDenKaisai(day['param']['url'], day['param']['param'])
                result = pk.parse()

                for race in result['races']:
                    pd = pr.ParserDenRace('/JRADB/accessD.html', race['param']['param'])
                    race = pd.parse()
                    print_race(race)

    else:
        pd = pr.ParserDenRace('/JRADB/accessD.html', args[1])
        race = pd.parse()
        print_race(race)
