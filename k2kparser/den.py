""" JRA Den (出馬表) Page Parsers

Output keys follow docs/naming.md.
"""
import logging
import re

from . import util
from . import parser


logger = logging.getLogger(__name__)


def _onclick_link(soup_anchor):
    """ Link from <a onclick="doAction(url, param)">, or None. """
    if soup_anchor is None or not soup_anchor.has_attr('onclick'):
        return None
    try:
        return util.Util.parse_func_params(soup_anchor['onclick'])
    except parser.ParseError:
        logger.info('Anchor parse error: ' + soup_anchor.getText())
        return None


def _href_link(soup_anchor):
    """ Link from <a href="url?CNAME=param">, or None. """
    if soup_anchor is None or not soup_anchor.has_attr('href'):
        return None
    try:
        return util.Util.format_params2(soup_anchor['href'])
    except (parser.ParseError, IndexError):
        logger.info('Anchor parse error: ' + soup_anchor.getText())
        return None


def _race_num(soup_img):
    return int(soup_img['alt'].replace('レース', ''))


def parse_kaisai_caption(soup_table):
    """ Caption of race_list table -> dict(date, weekday, kai, racecourse, nichi, weather, track_condition) """
    soup_caption = soup_table.find('caption')
    ret = util.parse_kaisai_header(soup_caption.find('div', attrs={'class': 'main'}).getText())

    soup_opt = soup_caption.find('div', attrs={'class': 'opt'})
    if soup_opt is not None:
        def li_text(tag):
            soup_li = soup_opt.find('li', attrs={'class': tag})
            soup_txt = soup_li.find('span', attrs={'class': 'txt'}) if soup_li else None
            return soup_txt.getText().strip() if soup_txt else None

        weather = li_text('weather')
        if weather:
            ret['weather'] = weather
        track_condition = {}
        turf = li_text('turf')
        if turf:
            track_condition['turf'] = turf
        dirt = li_text('durt') or li_text('dirt')    # JRA uses 'durt'
        if dirt:
            track_condition['dirt'] = dirt
        if track_condition:
            ret['track_condition'] = track_condition

    return ret


def parse_race_header(soup_unit):
    """ Common header of a single race page (den / result).
    :return: dict(date, weekday, kai, racecourse, nichi, race_num, departure, name, grade,
                  category, class, rule, weight_rule, distance, surface, course)
    """
    ret = util.parse_kaisai_header(soup_unit.find('div', attrs={'class': 'date'}).getText())
    ret['race_num'] = _race_num(soup_unit.find('div', attrs={'class': 'race_number'}).find('img'))
    ret['departure'] = util.to_hhmm(soup_unit.find('div', attrs={'class': 'time'}).getText())

    soup_name = soup_unit.find('span', attrs={'class': 'race_name'})
    ret['name'] = util.Util.trim_clean(soup_name.getText())
    soup_grade = soup_name.find('span', attrs={'class': 'grade_icon'})
    if soup_grade is not None and soup_grade.find('img') is not None:
        ret['grade'] = soup_grade.find('img')['alt']

    for key, css in (('category', 'category'), ('class', 'class'), ('rule', 'rule'), ('weight_rule', 'weight')):
        soup_div = soup_unit.find('div', attrs={'class': css})
        if soup_div is not None:
            text = util.Util.trim_clean(soup_div.getText())
            if text != '':
                ret[key] = text

    distance, course = util.Util.parse_course_distance(soup_unit.find('div', attrs={'class': 'course'}).getText())
    ret['distance'] = distance
    ret['surface'] = util.parse_surface(course)
    ret['course'] = course

    return ret


class ParserDenTop(parser.ParserKaisaiTop):
    """ 出馬表トップ: list of kaisai days. See ParserKaisaiTop.parse_content. """
    def __init__(self, path='/JRADB/accessD.html', param='pw01dli00/F3'):
        super().__init__(path, param)

    def get_base_soup(self, soup):
        return soup.find('div', attrs={'id': 'contentsBody'}).find('div', attrs={'id': 'main'})

    def parse_addtionl_in_day(self, soup_day, kaisai_info):
        soup_win5 = soup_day.find('div', attrs={'class': 'win5'})
        if soup_win5 is not None:
            link = _onclick_link(soup_win5.find('a'))
            if link is not None:
                kaisai_info['win5_link'] = link


class ParserDenKaisai(parser.ParserPost):
    def parse_content(self, soup):
        """ 開催ごとのレース一覧
        :return: dict
            'date', 'weekday', 'kai', 'racecourse', 'nichi'
            'weather': 天候
            'track_condition': {'turf': 芝の馬場状態, 'dirt': ダートの馬場状態}
            'races': list of dict
                'race_num', 'departure', 'name', 'condition', 'surface', 'distance', 'horse_count',
                'link': 出馬表, 'odds_link': オッズ, 'result_link': 結果
        """
        soup_table = soup.find('div', attrs={'id': 'contentsBody'}).find('table', attrs={'id': 'race_list'})
        ret = parse_kaisai_caption(soup_table)
        ret['races'] = []

        for soup_race in soup_table.find('tbody').find_all('tr'):
            race = {}
            race['race_num'] = _race_num(soup_race.find('th', attrs={'class': 'race_num'}).find('img'))
            race['departure'] = util.to_hhmm(soup_race.find('td', attrs={'class': 'time'}).getText())

            soup_names = soup_race.find('td', attrs={'class': 'race_name'}).find('div').find_all('div')
            race['name'] = util.Util.trim_clean(soup_names[0].getText())
            condition = util.Util.trim_clean(soup_names[1].getText())
            race['condition'] = condition if condition != '' else race['name']

            soup_dist = soup_race.find('td', attrs={'class': 'dist'})
            race['surface'] = util.parse_surface(soup_dist.find('span', attrs={'class': 'course'}).getText())
            race['distance'] = util.parse_int(soup_dist.find('span', attrs={'class': 'dist'}).getText())
            horse_count = util.parse_int(soup_dist.find('span', attrs={'class': 'num'}).getText())
            if horse_count is not None:
                race['horse_count'] = horse_count

            link = _href_link(soup_race.find('td', attrs={'class': 'syutsuba'}).find('a'))
            if link:
                race['link'] = link
            soup_odds = soup_race.find('td', attrs={'class': 'odds'})
            link = _onclick_link(soup_odds.find('a')) if soup_odds else None
            if link:
                race['odds_link'] = link
            soup_result = soup_race.find('td', attrs={'class': 'result'})
            link = _href_link(soup_result.find('a')) if soup_result else None
            if link:
                race['result_link'] = link

            ret['races'].append(race)

        return ret


class ParserDenRace(parser.ParserPost):
    def parse_horse(self, soup_tr):
        horse = {}

        soup_waku = soup_tr.find('td', attrs={'class': 'waku'})
        if soup_waku is not None and soup_waku.find('img') is not None:
            horse['waku'] = util.parse_int(soup_waku.find('img')['alt'])

        soup_num = soup_tr.find('td', attrs={'class': 'num'})
        if soup_num is not None:
            horse_num = util.parse_int(soup_num.getText())
            if horse_num is not None:
                horse['horse_num'] = horse_num

        soup_horse = soup_tr.find('td', attrs={'class': 'horse'})
        soup_name = soup_horse.find('div', attrs={'class': 'name'})
        horse['name'] = util.Util.trim_clean(soup_name.getText())
        link = _href_link(soup_name.find('a'))
        if link:
            horse['link'] = link

        soup_odds = soup_horse.find('div', attrs={'class': 'odds'})
        if soup_odds is not None:
            win_odds = util.parse_float(soup_odds.find('span', attrs={'class': 'num'}).getText()) \
                if soup_odds.find('span', attrs={'class': 'num'}) else None
            if win_odds is not None:
                horse['win_odds'] = win_odds
            soup_pop = soup_odds.find('span', attrs={'class': 'pop_rank'})
            popularity = util.parse_int(soup_pop.getText()) if soup_pop else None
            if popularity is not None:
                horse['popularity'] = popularity

        soup_weight = soup_horse.find('div', attrs={'class': 'weight'})
        if soup_weight is not None and soup_weight.getText().strip() != '':
            try:
                horse['body_weight'], horse['body_weight_diff'] = util.Util.parse_weight(soup_weight.getText())
            except ValueError:
                logger.warning('Failed to parse body weight: ' + soup_weight.getText())

        soup_owner = soup_horse.find('p', attrs={'class': 'owner'})
        if soup_owner is not None:
            horse['owner'] = util.Util.trim_clean(soup_owner.getText())

        soup_trainer = soup_horse.find('p', attrs={'class': 'trainer'})
        horse['trainer'] = util.person(util.Util.trim_clean(soup_trainer.getText()),
                                       _onclick_link(soup_trainer.find('a')))

        soup_sire = soup_horse.find('li', attrs={'class': 'sire'})
        if soup_sire is not None:
            horse['sire'] = util.Util.trim_clean(soup_sire.getText()).replace('父：', '')
        soup_mare = soup_horse.find('li', attrs={'class': 'mare'})
        if soup_mare is not None:
            soup_bms = soup_mare.find('span', attrs={'class': 'bloodmare'})
            if soup_bms is not None:
                horse['broodmare_sire'] = re.sub(r'[()（）]|母の父：', '', soup_bms.extract().getText()).strip()
            horse['dam'] = util.Util.trim_clean(soup_mare.getText()).replace('母：', '')

        soup_jockey_td = soup_tr.find('td', attrs={'class': 'jockey'})
        hande = util.parse_float(soup_jockey_td.find('p', attrs={'class': 'weight'}).getText())
        if hande is not None:
            horse['hande'] = hande
        soup_jockey = soup_jockey_td.find('p', attrs={'class': 'jockey'})
        horse['jockey'] = util.person(util.Util.trim_clean(soup_jockey.getText()), _onclick_link(soup_jockey.find('a')))

        parsed = util.Util.parse_age(soup_jockey_td.find('p', attrs={'class': 'age'}).getText())
        horse['age'] = parsed[0]
        horse['sex'] = parsed[1]
        if len(parsed) > 2:
            horse['coat'] = parsed[2]

        return horse

    def parse_content(self, soup):
        """ 出馬表（1レース）
        :return: dict
            'date', 'weekday', 'kai', 'racecourse', 'nichi', 'race_num', 'departure',
            'name', 'grade', 'category', 'class', 'rule', 'weight_rule', 'distance', 'surface', 'course',
            'odds_link', 'result_link',
            'horses': list of dict
                'waku', 'horse_num', 'name', 'link', 'win_odds', 'popularity',
                'body_weight', 'body_weight_diff', 'owner', 'trainer', 'sire', 'dam', 'broodmare_sire',
                'hande', 'jockey', 'age', 'sex', 'coat'
        """
        soup_syutsuba = soup.find('div', attrs={'id': 'contentsBody'}).find('div', attrs={'id': 'syutsuba'})
        race = parse_race_header(soup_syutsuba)

        soup_links = soup_syutsuba.find('div', attrs={'id': 'race_related_link'})
        if soup_links is not None:
            soup_li = soup_links.find('li', attrs={'class': 'result'})
            link = _href_link(soup_li.find('a')) if soup_li else None
            if link:
                race['result_link'] = link
            soup_li = soup_links.find('li', attrs={'class': 'odds'})
            link = _onclick_link(soup_li.find('a')) if soup_li else None
            if link:
                race['odds_link'] = link

        race['horses'] = [self.parse_horse(soup_tr)
                          for soup_tr in soup_syutsuba.find('tbody').find_all('tr')]

        return race
