""" JRA Odds (オッズ) Page Parsers

Output keys follow docs/naming.md.
"""
import logging
import re
from abc import ABCMeta, abstractmethod

from . import util
from . import parser
from . import den
from .den import _onclick_link


logger = logging.getLogger(__name__)

# ページ上の表記 -> 券種キー
BET_TYPE_TABLE = {
    '単勝・複勝': 'win',
    '単勝': 'win',
    '複勝': 'place',
    '枠連': 'wakuren',
    '馬連': 'umaren',
    'ワイド': 'wide',
    '馬単': 'umatan',
    '3連複': 'trio',
    '3連単': 'tierce',
}

# 開催ごとのレース一覧にある、オッズボタンの class 名 -> 券種キー
_BUTTON_CLASS_TABLE = {'tanpuku': 'win'}


def _odds_value(text):
    """ '12.3' -> 12.3 / '取消', '票数なし' など -> None """
    text = text.strip()
    try:
        return float(text.replace(',', ''))
    except ValueError:
        return None


class ParserOddsTop(parser.ParserKaisaiTop):
    """ オッズトップ: list of kaisai days. See ParserKaisaiTop.parse_content. """
    def __init__(self, path='/JRADB/accessD.html', param='pw15oli00/6D'):
        super().__init__(path, param)

    def get_base_soup(self, soup):
        return soup.find('div', attrs={'id': 'contentsBody'}).find('div', attrs={'class': 'thisweek'})


class ParserOddsKaisai(parser.ParserPost):
    def parse_content(self, soup):
        """ 開催ごとのレース一覧
        :return: dict
            'date', 'weekday', 'kai', 'racecourse', 'nichi'
            'races': list of dict
                'race_num', 'name', 'condition',
                'odds_links': {券種: link}  (win / wakuren / umaren / wide / umatan / trio / tierce)
        """
        soup_table = soup.find('div', attrs={'id': 'contentsBody'}).find('table', attrs={'id': 'race_list'})
        ret = den.parse_kaisai_caption(soup_table)
        ret['races'] = []

        for soup_race in soup_table.find('tbody').find_all('tr'):
            race = {}
            race['race_num'] = int(soup_race.find('a').find('img')['alt'].replace('レース', ''))

            soup_names = soup_race.find('td', attrs={'class': 'race_name'}).find('div').find_all('div')
            race['name'] = util.Util.trim_clean(soup_names[0].getText())
            condition = util.Util.trim_clean(soup_names[1].getText())
            race['condition'] = condition if condition != '' else race['name']

            odds_links = {}
            for soup_button in soup_race.find('div', attrs={'class': 'btn_list'}).find_all('div'):
                link = _onclick_link(soup_button.find('a'))
                if link is not None and soup_button.has_attr('class'):
                    css = soup_button['class'][0]
                    odds_links[_BUTTON_CLASS_TABLE.get(css, css)] = link
            race['odds_links'] = odds_links

            ret['races'].append(race)

        return ret


class OddsParser(parser.ParserPost, metaclass=ABCMeta):
    """ Base of single-race odds pages.
    parse_content returns dict
        'odds_links': {券種: link}
        'odds': 券種ごとの形（各サブクラス参照）
        'votes': {券種: 票数, 'total': 総票数}  (ページにある場合)
        'updated_at': 'HH:MM' オッズ更新時刻
    """
    def parse_odds_links(self, soup_area):
        links = {}
        soup_ul = soup_area.find('ul', attrs={'class': 'pills'})
        if soup_ul is None:
            return links
        for soup_li in soup_ul.find_all('li'):
            soup_anchor = soup_li.find('a')
            if soup_anchor is None:
                continue
            tag = util.Util.trim_clean(soup_anchor.getText())
            if tag in BET_TYPE_TABLE:
                link = _onclick_link(soup_anchor)
                if link is not None:
                    links[BET_TYPE_TABLE[tag]] = link
        return links

    @abstractmethod
    def parse_odds_content(self, soup_area):
        pass

    def parse_odds_votes(self, soup_vote):
        votes = {}
        for soup_tr in soup_vote.find('tbody').find_all('tr'):
            th = util.Util.trim_clean(soup_tr.find('th').getText())
            value = util.parse_int(soup_tr.find('td').getText())
            if '合計' in th:
                votes['total'] = value
            elif th in BET_TYPE_TABLE:
                votes[BET_TYPE_TABLE[th]] = value
            else:
                logger.warning('Unknown tag found in vote : ' + th)
        return votes

    def parse_content(self, soup):
        soup_area = soup.find('div', attrs={'id': 'contentsBody'})

        ret = {
            'odds_links': self.parse_odds_links(soup_area),
            'odds': self.parse_odds_content(soup_area),
        }

        soup_vote = soup_area.find('div', attrs={'id': 'votes'})
        if soup_vote is not None:
            ret['votes'] = self.parse_odds_votes(soup_vote)

        soup_refresh = soup_area.find('div', attrs={'class': 'refresh_line'})
        soup_time = soup_refresh.find('div', attrs={'class': 'time'}) if soup_refresh else None
        if soup_time is not None:
            updated_at = util.to_hhmm(soup_time.getText())
            if updated_at:
                ret['updated_at'] = updated_at

        return ret

    @classmethod
    def parse_pair_tables(cls, soup_lis, first_of):
        """ Tables whose caption (or image) is the first horse/waku and rows are the second.
        :return: {'1-2': odds or None}
        """
        odds = {}
        for soup_li in soup_lis:
            first = first_of(soup_li)
            for soup_tr in soup_li.find_all('tr'):
                td = soup_tr.find('td').getText().strip()
                if td == '':
                    continue
                odds['{}-{}'.format(first, soup_tr.find('th').getText().strip())] = _odds_value(td)
        return odds


class OddsParserWin(OddsParser):
    def parse_odds_content(self, soup_area):
        """ 単勝・複勝
        :return: list of dict
            'waku', 'horse_num',
            'win': 単勝オッズ (取消は None),
            'place': {'min': 複勝の下限, 'max': 複勝の上限} (取消は None)
        """
        soup_table = soup_area.find('table', attrs={'class': 'tanpuku'})
        waku = 0
        horses = []
        for soup_tr in soup_table.find('tbody').find_all('tr'):
            soup_waku = soup_tr.find('td', attrs={'class': 'waku'})
            if soup_waku is not None and soup_waku.find('img') is not None:
                waku = util.parse_int(soup_waku.find('img')['alt'])   # rowspan: carries over to next rows

            horse = {'waku': waku,
                     'horse_num': int(soup_tr.find('td', attrs={'class': 'num'}).getText())}
            horse['win'] = _odds_value(soup_tr.find('td', attrs={'class': 'odds_tan'}).getText())

            soup_place = soup_tr.find('td', attrs={'class': 'odds_fuku'})
            soup_min = soup_place.find('span', attrs={'class': 'min'})
            soup_max = soup_place.find('span', attrs={'class': 'max'})
            if soup_min is not None and soup_max is not None:
                horse['place'] = {'min': _odds_value(soup_min.getText()), 'max': _odds_value(soup_max.getText())}
            else:
                horse['place'] = None

            horses.append(horse)

        return horses


class OddsParserBracketQuinella(OddsParser):
    def parse_odds_content(self, soup_area):
        """ 枠連: {'1-2': odds} """
        soup_lis = soup_area.find('ul', attrs={'class': 'waku_list'}).find_all('li')
        return self.parse_pair_tables(
            soup_lis, lambda soup_li: re.sub(r'[^0-9]', '', soup_li.find('table').find('img')['alt']))


class OddsParserBracket(OddsParser):
    """ 馬連: {'1-2': odds} """
    list_class_tag = 'umaren_list'

    def parse_odds_content(self, soup_area):
        soup_lis = [soup_li for soup_ul in soup_area.find_all('ul', attrs={'class': self.list_class_tag})
                    for soup_li in soup_ul.find_all('li')]
        return self.parse_pair_tables(
            soup_lis, lambda soup_li: soup_li.find('table').find('caption').getText().strip())


class OddsParserExacta(OddsParserBracket):
    """ 馬単: {'1-2': odds}（1着-2着） """
    list_class_tag = 'umatan_list'


class OddsParserWide(OddsParser):
    def parse_odds_content(self, soup_area):
        """ ワイド: {'1-2': {'min': 下限, 'max': 上限}}（取消などは None） """
        odds = {}
        for soup_ul in soup_area.find_all('ul', attrs={'class': 'wide_list'}):
            for soup_li in soup_ul.find_all('li'):
                first = soup_li.find('table').find('caption').getText().strip()
                for soup_tr in soup_li.find_all('tr'):
                    key = '{}-{}'.format(first, soup_tr.find('th').getText().strip())
                    soup_td = soup_tr.find('td')
                    soup_min = soup_td.find('span', attrs={'class': 'min'})
                    soup_max = soup_td.find('span', attrs={'class': 'max'})
                    if soup_min is None or soup_max is None:
                        if soup_td.getText().strip() != '':
                            odds[key] = None
                        continue
                    if soup_min.getText().strip() == '':
                        continue
                    odds[key] = {'min': _odds_value(soup_min.getText()), 'max': _odds_value(soup_max.getText())}
        return odds


class OddsParserTrio(OddsParser):
    def parse_odds_content(self, soup_area):
        """ 3連複: {'1-2-3': odds} """
        odds = {}
        soup_odds_list = soup_area.find('div', attrs={'id': 'odds_list'})
        for soup_unit in soup_odds_list.find_all('div', attrs={'class': 'fuku3_unit'}):
            for soup_ul in soup_unit.find_all('ul', attrs={'class': 'fuku3_list'}):
                for soup_li in soup_ul.find_all('li'):
                    first = soup_li.find('caption').getText().strip()
                    for soup_tr in soup_li.find_all('tr'):
                        td = soup_tr.find('td').getText().strip()
                        if td == '':
                            continue
                        odds['{}-{}'.format(first, soup_tr.find('th').getText().strip())] = _odds_value(td)
        return odds


class OddsParserTierce(OddsParser):
    def parse_odds_content(self, soup_area):
        """ 3連単: {'1-2-3': odds}（1着-2着-3着） """
        odds = {}
        soup_odds_list = soup_area.find('div', attrs={'id': 'odds_list'})
        for soup_unit in soup_odds_list.find_all('div', attrs={'class': 'tan3_unit'}):
            for soup_li in soup_unit.find_all('li'):
                soup_nums = soup_li.find_all('div', attrs={'class': 'num'})
                if len(soup_nums) != 2:
                    logger.error('Not enough pairs')
                    continue
                prefix = '{}-{}'.format(soup_nums[0].getText().strip(), soup_nums[1].getText().strip())
                for soup_tr in soup_li.find_all('tr'):
                    td = soup_tr.find('td').getText().strip()
                    if td == '':
                        continue
                    odds['{}-{}'.format(prefix, soup_tr.find('th').getText().strip())] = _odds_value(td)
        return odds
