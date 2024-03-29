""" JRA Den Page Top Parser """
import logging
import re

from . import util
from . import parser


logger = logging.getLogger(__name__)

class ParserDenTop(parser.ParserKaisaiTop):
    def __init__(self, path='/JRADB/accessD.html', param='pw01dli00/F3'):
        super().__init__(path, param)

    def get_base_soup(self, soup):
        soup_area = soup.find('div', attrs={'id': 'contentsBody'})

        soup_main= soup_area.find('div', attrs={'id': 'main'})

        return soup_main

    def parse_addtionl_in_day(self, soup_day, kaisai_info):
        soup_win5 = soup_day.find('div', attrs={'class': 'win5'})
        if soup_win5 is not None:
            soup_anchor = soup_win5.find('a')
            if soup_anchor is not None:
                if soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                        kaisai_info['win5_link'] = params
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())


    # parse_content output
    """ Parse content and return parameters if exist
    :param soup:
    :return: Array of Dict of Kaisai
        'date': 日付
        'weekday': 曜日
        'kaisai': Array of Kaisai information
            'index': 開催回数
            'day': 開催日（何日目）
            'place': 競馬場
            'params': URL and Post parameter

    """


class ParserDenKaisai(parser.ParserPost):
    @classmethod
    def get_li_text(cls, soup_parent, tag):
        soup_li = soup_parent.find('li', attrs={'class': tag})
        if soup_li is not None:
            soup_span = soup_li.find('span', attrs={'class': 'txt'})
            if soup_span is not None:
                return soup_span.getText().strip()


        return None


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

        soup_caption_opt = soup_caption.find('div', attrs={'class': 'opt'})
        if soup_caption_opt is not None:
            weather = ParserDenKaisai.get_li_text(soup_caption_opt, 'weather')
            if weather is not None:
                kaisai_list['weather'] = weather

            durt = ParserDenKaisai.get_li_text(soup_caption_opt, 'durt')
            if durt is not None:
                kaisai_list['dirt'] = durt
                # JRA contents might have typo.

            turf = ParserDenKaisai.get_li_text(soup_caption_opt, 'turf')
            if turf is not None:
                kaisai_list['turf'] = turf

        kaisai_list['races'] = []

        soup_tbody = soup_table.find('tbody')
        soup_races = soup_tbody.find_all('tr')
        for soup_race in soup_races:
            race = {}
            soup_time = soup_race.find('td', attrs={'class': 'time'})
            soup_race_name_td = soup_race.find('td', attrs={'class': 'race_name'})
            soup_race_name = soup_race_name_td.find('div').find_all('div')
            race_name = util.Util.trim_clean(soup_race_name[0].getText())
            race_cond = util.Util.trim_clean(soup_race_name[1].getText())
            if race_cond == '':
                race_cond = race_name

            soup_dist_group = soup_race.find('td', attrs={'class': 'dist'})

            soup_num = soup_dist_group.find('span', attrs={'class': 'num'})
            uma_num = int(soup_num.getText().replace('頭',''))
            soup_dist = soup_dist_group.find('span', attrs={'class': 'dist'})
            dist = int(soup_dist.getText().replace(',','').replace('m',''))
            soup_course = soup_dist_group.find('span', attrs={'class': 'course'})

            soup_shutuba = soup_race.find('td', attrs={'class': 'syutsuba'})
            soup_anchor = soup_shutuba.find('a')
            race['link'] = util.Util.format_params2(soup_anchor['href'])


            soup_odds = soup_race.find('td', attrs={'class': 'odds'})
            if soup_odds is not None:
                soup_anchor = soup_odds.find('a')
                if soup_anchor is not None:
                    assert soup_anchor.has_attr('onclick')
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                        race['odds_link'] = params
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())
                        assert False

            soup_result = soup_race.find('td', attrs={'class': 'result'})
            if soup_result is not None:
                soup_anchor = soup_result.find('a')
                if soup_anchor is not None:
                    race['result'] = util.Util.format_params2(soup_anchor['href'])

            soup_img = soup_race.find('th', attrs={'class': 'race_num'}).find('img')
            race_index = int(soup_img['alt'].replace('レース', ''))

            race['index'] = race_index
            race['departure'] = soup_time.getText()
            race['course'] = soup_course.getText()
            race['name'] = race_name
            race['cond'] = race_cond
            race['uma_num'] = uma_num
            race['dist'] = dist
            kaisai_list['races'].append(race)

        return kaisai_list


class ParserDenRace(parser.ParserPost):
    def parse_content(self, soup):
        """ Parse content and return race den info
                :param soup:
                :return:Race Den info
                    'date': 日付
                    'weekday': 曜日
                    'index': 開催回数
                    'nichisuu': 開催日数
                    'place': 場所
                    'departure': 発走時刻
                    'category': レースカテゴリ
                    'class': レースクラス
                    'rule': レースルール
                    'weight': 斤量条件
                    'distance': 距離
                    'course': コース
                    'horses': Array of horse
                        'waku': 枠番
                        'num': 馬番
                        'name': 馬名
                        'url': url情報
                        'weight': 馬体重
                        'weight_diff': 馬体重増減
                        'trainer': 調教師
                            'name': 調教師名
                            'url': url情報
                        'sire': 父
                        'mare': 母
                        'bms': 母父
                        'hande': 斤量
                        'jockey': 騎手
                            'name': 騎手名
                            'url': url情報
                        'age': 馬齢
                        'sex': 性別
                        'hair': 毛色
        """

        race = {}

        soup_area = soup.find('div', attrs={'id': 'contentsBody'})
        soup_syutsuba = soup_area.find('div', attrs={'id': 'syutsuba'})
        soup_date = soup_syutsuba.find('div', attrs={'class': 'date'})
        date, weekday, index, place, nichisuu = util.Util.parse_kaisai_date(soup_date.getText())

        race['date'] = date
        race['weekday'] = weekday
        race['index'] = index
        race['place'] = place
        race['nichisuu'] = nichisuu

        race['departure'] = soup_syutsuba.find('div', attrs={'class': 'time'}).find('strong').getText()

        race['index'] = int(soup_syutsuba.find('div', attrs={'class': 'race_number'}).
                         find('img')['alt'].replace('レース', ''))

        soup_name = soup_syutsuba.find('span', attrs={'class': 'race_name'})
        race['name'] = util.Util.trim_clean(soup_name.getText())

        soup_grade = soup_name.find('span', attrs={'class': 'grade_icon'})
        if soup_grade is None:
            logger.debug('None Grade Race')
        else:
            race['grade'] = soup_grade.find('img')['alt']


        race['category'] = soup_syutsuba.find('div', attrs={'class': 'category'}).getText()
        race['class'] = soup_syutsuba.find('div', attrs={'class': 'class'}).getText()
        race['rule'] = soup_syutsuba.find('div', attrs={'class': 'rule'}).getText()
        race['weight'] = soup_syutsuba.find('div', attrs={'class': 'weight'}).getText()
        distance, course = \
            util.Util.parse_course_distance(soup_syutsuba.find('div', attrs={'class': 'course'}).getText())
        race['distance'] = distance
        race['course'] = course

        soup_links = soup_syutsuba.find('div', attrs={'id': 'race_related_link'})

        soup_result_link = soup_links.find('li', attrs={'class': 'result'})
        if soup_result_link is not None:
            soup_anchor = soup_result_link.find('a')
            if soup_anchor is not None and soup_anchor.has_attr('href'):
                try:
                    race['result_link'] = util.Util.format_params2(soup_anchor['href'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())


        soup_odds_link = soup_links.find('li', attrs={'class': 'odds'})
        if soup_odds_link is not None:
            soup_anchor = soup_odds_link.find('a')
            if soup_anchor.has_attr('onclick'):
                try:
                    race['odds_link'] = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

        soup_tbody = soup_syutsuba.find('tbody')
        soup_trs = soup_tbody.find_all('tr')

        race['horses'] = []
        for soup_tr in soup_trs:
            hourse = {}
            soup_td_waku = soup_tr.find('td', attrs={'class': 'waku'})
            if soup_td_waku is not None:
                soup_img = soup_td_waku.find('img')
                if soup_img is not None:
                    try :
                        waku = int(re.sub(r'[^0-9]', '', soup_img['alt']))
                        hourse['waku'] = waku
                    except ValueError:
                        logger.error('Failed to get Waku Number : ' + soup_td_waku)


            soup_td_num = soup_tr.find('td', attrs={'class': 'num'})
            if soup_td_num is not None:
                td_num = soup_td_num.getText().strip()
                if td_num != '':
                    try :
                        num = int(td_num)
                        hourse['num'] = num
                    except ValueError:
                        logger.error('Failed to get Uma Number : ' + td_num)

            soup_horse_td = soup_tr.find('td', attrs={'class': 'horse'})
            soup_name = soup_horse_td.find('div', attrs={'class': 'name'})
            hourse['name'] = util.Util.trim_clean(soup_name.getText())
            soup_anchor = soup_name.find('a')
            if soup_anchor is not None and soup_anchor.has_attr('href'):
                try:
                    hourse['link'] = util.Util.format_params2(soup_anchor['href'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

            try:
                odds, odds_rank = util.Util.parse_odds(soup_horse_td.find('div', attrs={'class': 'odds'}).getText())
                hourse['odds'] = odds
                hourse['odds_rank'] = odds_rank
            except:
                pass

            soup_weight = soup_horse_td.find('div', attrs={'class': 'weight'})
            if soup_weight is not None and soup_weight.getText() != '':
                try:
                    weight, weight_diff = util.Util.parse_weight(soup_weight.getText())
                    hourse['weight'] = weight
                    hourse['weight_diff'] = weight_diff
                except:
                    logger.error('Failed to parse weight and weight diff : ' + soup_weight.getText())

            soup_owner = soup_horse_td.find('p', attrs={'class': 'owner'})
            if soup_owner is not None:
                hourse['owner'] = soup_owner.getText()

            soup_trainer = soup_horse_td.find('p', attrs={'class': 'trainer'})
            trainer = {}
            trainer['name'] = util.Util.trim_clean(soup_trainer.getText())
            soup_anchor = soup_trainer.find('a')
            if soup_anchor is not None and soup_anchor.has_attr('onclick'):
                try:
                    trainer['link'] = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

            hourse['trainer'] = trainer

            hourse['sire'] = util.Util.trim_clean(soup_horse_td.find('li', attrs={'class': 'sire'}).getText()).replace('父：','')
            mare_info = util.Util.trim_clean(soup_horse_td.find('li', attrs={'class': 'mare'}).getText()).split(' ')
            hourse['mare'] = mare_info[0].replace('母：','')
            hourse['bms'] = mare_info[-1].replace('(母の父：','').replace(')','')

            # Parse Jokey Block
            soup_jokey_td = soup_tr.find('td', attrs={'class': 'jockey'})
            hande_value = util.Util.trim_clean(
                soup_jokey_td.find('p', attrs={'class': 'weight'}).getText()).replace('kg', '')
            try:
                hourse['hande'] = float(hande_value)
            except ValueError:
                logger.warning('Convert Error : {}'.format(hande_value))

            soup_jockey = soup_jokey_td.find('p', attrs={'class': 'jockey'})
            jockey = {}
            jockey['name'] = util.Util.trim_clean(soup_jockey.getText())
            soup_anchor = soup_jockey.find('a')
            if soup_anchor is not None and soup_anchor.has_attr('onclick'):
                try:
                    jockey['link'] = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

            hourse['jockey'] = jockey

            age, sex, hair = util.Util.parse_age(soup_jokey_td.find('p', attrs={'class': 'age'}).getText())
            hourse['age'] = age
            hourse['sex'] = sex
            hourse['hair'] = hair

            race['horses'].append(hourse)


        return race