import parser as pr

if __name__ == '__main__':
    p = pr.ParserDenTop('/JRADB/accessD.html', 'pw01dli00/F3')
    kaisai_list = p.parse()

    for kaisai in kaisai_list:
        for day in kaisai['kaisai']:
            pk = pr.ParserDenKaisai(day['param']['url'], day['param']['param'])
            result = pk.parse()

            print('日付 :', result['date'])
            print(' {}回{}{}日'.format(result['index'], result['place'], result['nichisuu']))

            for race in result['races']:
                print(' ' * 2 ,'{}レース {}'.format(race['index'], race['name']))