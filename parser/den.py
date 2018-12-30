""" JRA Den Page Top Parser """
from logging import getLogger

from . import parser
from . import util


logger = getLogger(__name__)

class ParserDenTop(parser.ParserPost):
    def __init__(self, path, param):
        super().__init__(path, param)

    def parse_content(self, soup):
        """ Parse content and return parameters if exist
        :param soup:
        :return: Array of Dict of Kaisai
            'date': 日付
            'kaisai': Array of Kaisai information
                'index': 開催回数
                'day': 開催日（何日目）
                'place': 競馬場
                'params': URL and Post parameter

        """
        soup_area = soup.find('div', attrs = {'id':'contentsBody'})
        soup_day_area = soup_area.find('div', attrs = {'id':'main'})
        soup_days = soup_day_area.find_all('div', attrs = {'class':'panel'})
        kaisai_list = []
        for soup_day in soup_days:
            kaisai_info = {}
            header = util.Util.trim_clean(soup_day.find('h3').getText())

            kaisai_info['date'] = header
            kaisai_info['kaisai'] = []

            soup_kaisai_list = soup_day.find_all('li', attrs = {'class':'waku'})
            for soup_kaisai in soup_kaisai_list:
                kaisai_info_day = {}
                soup_anchor = soup_kaisai.find('a')
                if soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())

                try:
                    kaisai_param = util.Util.parse_kaisai(soup_kaisai.getText())
                except ValueError:
                    logger.info('parse_kaisai error: ' + soup_kaisai.getText())

                kaisai_info_day['index'] = kaisai_param[0]
                kaisai_info_day['day'] = kaisai_param[1]
                kaisai_info_day['place'] = kaisai_param[2]
                kaisai_info_day['param'] = util.Util.format_params(params)

                kaisai_info['kaisai'].append(kaisai_info_day)

            kaisai_list.append(kaisai_info)

        return kaisai_list


class ParserDenKaisai(parser.ParserPost):
    def __init__(self, path, param):
        super().__init__(path, param)

    def parse_content(self, soup):
        """ Parse content and return kaisai race list
        :param soup:
        :return: Array of Dict of Kaisai Race
            'date': 日付
            'weekday': 曜日
            'index': 開催回数
            'nichisuu': 開催日数
            'place': 場所
            'races': Array of race
                'index': レース番号
                'departure': 発走時刻
                'course': コース
                'dist': 距離
                'name': レース名
                'cond': レース条件
                'uma_num': 出走頭数
                'param' URL and Post parameter
        """

        kaisai_list = {}

        soup_area = soup.find('div', attrs={'id': 'contentsBody'})
        soup_table = soup_area.find('table', attrs={'id': 'race_list'})
        soup_caption = soup_table.find('caption')
        soup_caption_main = soup_caption.find('div', attrs={'class': 'main'})
        date, weekday, index, place, nichisuu = util.Util.parse_kaisai_date(soup_caption_main.getText())
        kaisai_list['date'] = date
        kaisai_list['weekday'] = weekday
        kaisai_list['index'] = index
        kaisai_list['place'] = place
        kaisai_list['nichisuu'] = nichisuu
        kaisai_list['races'] = []

        soup_tbody = soup_table.find('tbody')
        soup_races = soup_tbody.find_all('tr')
        for soup_race in soup_races:
            race = {}
            soup_time = soup_race.find('td', attrs={'class': 'time'})
            soup_course = soup_race.find('td', attrs={'class': 'course'})
            soup_race_name = soup_race.find('td', attrs={'class': 'race_name'}).find_all('li')
            race_name = util.Util.trim_clean(soup_race_name[0].getText())
            race_cond = util.Util.trim_clean(soup_race_name[1].getText())
            if race_cond == '':
                race_cond = race_name
            soup_num = soup_race.find('td', attrs={'class': 'num'})
            uma_num = int(soup_num.getText().replace('頭',''))
            soup_dist = soup_race.find('td', attrs={'class': 'dist'})
            dist = int(soup_dist.getText().replace('メートル', '').replace(',',''))

            soup_anchor = soup_race.find('a')
            if soup_anchor.has_attr('onclick'):
                try:
                    params = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

            soup_img = soup_anchor.find('img')
            race_index = int(soup_img['alt'].replace('レース', ''))

            race['index'] = race_index
            race['departure'] = soup_time.getText()
            race['course'] = soup_course.getText()
            race['name'] = race_name
            race['cond'] = race_cond
            race['uma_num'] = uma_num
            race['dist'] = dist
            race['param'] = util.Util.format_params(params)
            kaisai_list['races'].append(race)

        return kaisai_list