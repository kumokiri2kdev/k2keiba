""" JRA Odds Page Parser """
import logging
import re
from abc import ABCMeta, abstractmethod

from . import util
from . import parser


logger = logging.getLogger(__name__)

exchange_table = {
    '単勝・複勝': 'win',
    '枠連': 'wakuren',
    '馬連': 'umaren',
    'ワイド': 'wide',
    '馬単': 'umatan',
    '3連複': 'trio',
    '3連単': 'tierce',
}

class ParserOddsTop(parser.ParserKaisaiTop):
    def __init__(self, path='/JRADB/accessD.html', param='pw15oli00/6D'):
        super().__init__(path, param)

    def get_base_soup(self, soup):
        soup_area = soup.find('div', attrs={'id': 'contentsBody'})
        soup_thisweek = soup_area.find('div', attrs={'class': 'thisweek'})

        return soup_thisweek

class ParserOddsKaisai(parser.ParserPost):
    def parse_content(self, soup):
        """ Parse content and return kaisai odds list
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
                'name': レース名
                'cond': レース条件
                'params' Dict of odds params
                    'tanpuku': 単複 URL and Post parameter
                    'wakuren': 枠連 URL and Post parameter
                    'umaren': 馬連 URL and Post parameter
                    'umatan': 馬単 URL and Post parameter
                    'wide': ワイド URL and Post parameter
                    'trio': 三連複 URL and Post parameter
                    'tierce': 三連単 URL and Post parameter

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
            soup_race_name = soup_race.find('td', attrs={'class': 'race_name'}).find('div').find_all('div')
            race_name = util.Util.trim_clean(soup_race_name[0].getText())
            race_cond = util.Util.trim_clean(soup_race_name[1].getText())
            if race_cond == '':
                race_cond = race_name

            soup_anchor = soup_race.find('a')
            soup_img = soup_anchor.find('img')
            race_index = int(soup_img['alt'].replace('レース', ''))

            race['index'] = race_index
            race['name'] = race_name
            race['cond'] = race_cond

            soup_odds_link_div = soup_race.find('div', attrs={'class': 'btn_list'})
            soup_odds_link_divs = soup_odds_link_div.find_all('div')
            odds_params = {}
            for soup_odds_link in soup_odds_link_divs:
                soup_anchor = soup_odds_link.find('a')
                if soup_anchor is not None and soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                        odds_params[soup_odds_link['class'][0]] = params
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())

            race['odds_params'] = odds_params

            kaisai_list['races'].append(race)

        return kaisai_list


class OddsParser(parser.ParserPost, metaclass=ABCMeta):
    def parse_odds_links(self, soup_area):
        soup_ul = soup_area.find('ul', attrs={'class': 'pills'})
        soup_lis = soup_ul.find_all('li')
        links = {}
        for soup_li in soup_lis:
            soup_anchor = soup_li.find('a')
            if soup_anchor is not None:
                tag = util.Util.trim_clean(soup_anchor.getText())
                if tag in exchange_table and soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                        links[exchange_table[tag]] = params
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + tag)

        return links

    @abstractmethod
    def parse_odds_content(self, soup_area):
        pass

    def parse_odds_vote(self, soup_vote):
        soup_tbody = soup_vote.find('tbody')
        soup_trs = soup_tbody.find_all('tr')
        vote = {}

        soup_tr = soup_trs[0]
        tag = soup_tr.find('th').getText().strip()
        if tag in exchange_table:
            tag = exchange_table[tag]
        else:
            logger.warning('Unknown tag found in vote : ' + th)

        td = int(soup_tr.find('td').getText().strip().replace(',', ''))
        vote[tag] = td

        soup_tr = soup_trs[1]
        td = int(soup_tr.find('td').getText().strip().replace(',', ''))
        vote['total'] = td

        return vote

    def parse_content(self, soup):
        odds = {}
        soup_area = soup.find('div', attrs={'id': 'contentsBody'})

        odds['links'] = self.parse_odds_links(soup_area)

        odds['odds'] = self.parse_odds_content(soup_area)

        soup_vote = soup_area.find('div', attrs={'id': 'votes'})
        if soup_vote is not None:
            odds['vote'] = self.parse_odds_vote(soup_vote)

        # ToDo : Observe running odds
        soup_reflresh = soup_area.find('div', attrs={'class': 'refresh_line'})
        if soup_reflresh:
            odds['refresh'] = util.Util.trim_clean(soup_reflresh.getText())
            soup_time = soup_reflresh.find('div', attrs={'class': 'time'})
            if soup_time:
                odds['time'] = util.Util.trim_clean(soup_time.getText())

        return odds


class OddsParserWin(OddsParser):
    def parse_odds_links(self, soup_area):
        soup_ul = soup_area.find('ul', attrs={'class': 'pills'})
        soup_lis = soup_ul.find_all('li')
        links = {}
        for soup_li in soup_lis:
            soup_anchor = soup_li.find('a')
            if soup_anchor is not None:
                tag = util.Util.trim_clean(soup_anchor.getText())
                if tag in exchange_table and soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                        links[exchange_table[tag]] = params
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + tag)

        return links

    def parse_odds_winplace(self, soup_table):
        soup_tbody = soup_table.find('tbody')
        soup_trs = soup_tbody.find_all('tr')

        waku = 0
        horses = []
        for soup_tr in soup_trs:
            horse = {}
            soup_td_waku = soup_tr.find('td', attrs={'class': 'waku'})
            if soup_td_waku is not None:
                soup_img = soup_td_waku.find('img')
                waku = int(re.sub(r'[^0-9]', '', soup_img['alt']))
            horse['waku'] = waku

            horse['num'] = int(soup_tr.find('td', attrs={'class': 'num'}).getText())

            win = soup_tr.find('td', attrs={'class': 'odds_tan'}).getText()
            if win != '取消' and win is not None:
                try:
                    horse['win'] = float(win)
                except:
                    logging.debug('Win is not number')

            soup_place = soup_tr.find('td', attrs={'class': 'odds_fuku'})
            if soup_place.getText() != '取消':
                place = {}
                horse['place'] = place
                place_min = soup_place.find('span', attrs={'class': 'min'}).getText()
                try :
                    place['min'] = float(place_min)
                except:
                    logging.debug('Place Min is not number')

                place_max = soup_place.find('span', attrs={'class': 'max'}).getText()
                try :
                    place['max'] = float(place_max)
                except:
                    logging.debug('Place Max is not number')

            horses.append(horse)

        return horses

    def parse_odds_vote(self, soup_vote):
        soup_tbody = soup_vote.find('tbody')
        soup_trs = soup_tbody.find_all('tr')
        vote = {}

        for soup_tr in soup_trs:
            th = soup_tr.find('th').getText()
            td = int(soup_tr.find('td').getText().replace(',',''))
            if th == '単勝':
                vote['win'] = td
            elif th == '複勝':
                vote['place'] = td
            elif th == '総票数合計':
                vote['total'] = td
            else:
                logger.warning('Unknown tag found in vote : ' + th)

        return vote

    def parse_odds_content(self, soup_area):
        soup_table = soup_area.find('table', attrs={'class': 'tanpuku'})
        horses = self.parse_odds_winplace(soup_table)

        return horses

    # parse_content output
    """ Parse content and return odds win info if exist
    :param soup:
    :return: Array of Dict of Odds Win
        'links': URLs
            'win': 単勝・複勝 URL and Post parameter
            'umaren': 馬連 URL and Post parameter
            'wide': 馬連 URL and Post parameter
            'umatan': 馬連 URL and Post parameter
            'trio': 馬連 URL and Post parameter
            'tierce': 馬連 URL and Post parameter
        'odds': Array of Horse Odds
            'waku': 枠順
            'num': 馬番
            'win': 単勝オッズ
            'place': 複勝オッズ
                'min': 最低オッズ
                'max': 最大オッズ
        'vote': 全体投票情報
            'win': 単勝投票数
            'place': 複勝投票数
            'total': 単勝 + 複勝投票数
    """

class OddsParserBracketQuinella(OddsParser):
    def parse_odds_content(self, soup_area):
        soup_ul = soup_area.find('ul', attrs={'class': 'waku_list'})
        soup_lis = soup_ul.find_all('li')

        odds = {}
        for soup_li in soup_lis:
            soup_table = soup_li.find('table')
            soup_img = soup_table.find('img')
            tag_1 = re.sub(r'[^0-9]', '', soup_img['alt'])
            soup_trs = soup_li.find_all('tr')
            for soup_tr in soup_trs:
                th = soup_tr.find('th').getText().strip()
                td = soup_tr.find('td').getText().strip()
                if td == '':
                    continue
                else:
                    try:
                        odds_val = float(td)
                    except ValueError:
                        logger.debug('Float Convertion Error: ' + soup_tr.find('th').getText().strip())
                        odds_val = td

                odds[tag_1 + '-' + th] = odds_val

        return odds

    # parse_content output
    """ Parse content and return odds win info if exist
    :param soup:
    :return: Array of Dict of Odds Win
        'links': URLs
            'win': 単勝・複勝 URL and Post parameter
            'umaren': 馬連 URL and Post parameter
            'wide': 馬連 URL and Post parameter
            'umatan': 馬連 URL and Post parameter
            'trio': 馬連 URL and Post parameter
            'tierce': 馬連 URL and Post parameter
        'odds': Dict of Wakuren Odds {枠版組み合わせ : オッズ}
        'vote': 全体投票情報
            'wakuren': 枠連投票数
            'total': 単勝 + 複勝投票数
    """

class OddsParserBracket(OddsParser):
    list_class_tag = 'umaren_list'
    def parse_odds_content(self, soup_area):
        soup_uls = soup_area.find_all('ul', attrs={'class': self.list_class_tag})
        odds = {}

        for soup_ul in soup_uls:
            soup_lis = soup_ul.find_all('li')

            for soup_li in soup_lis:
                soup_table = soup_li.find('table')
                tag_1 = soup_table.find('caption').getText().strip()
                soup_trs = soup_li.find_all('tr')
                for soup_tr in soup_trs:
                    th = soup_tr.find('th').getText().strip()
                    td = soup_tr.find('td').getText().strip()
                    if td == '':
                        continue
                    else:
                        try:
                            odds_val = float(td)
                        except ValueError:
                            logger.debug('Float Convertion Error: ' + soup_tr.find('th').getText().strip())
                            odds_val = td

                    odds[tag_1 + '-' + th] = odds_val

        return odds

    # parse_content output
    """ Parse content and return odds win info if exist
    :param soup:
    :return: Array of Dict of Odds Win
        'links': URLs
            'win': 単勝・複勝 URL and Post parameter
            'umaren': 馬連 URL and Post parameter
            'wide': 馬連 URL and Post parameter
            'umatan': 馬連 URL and Post parameter
            'trio': 馬連 URL and Post parameter
            'tierce': 馬連 URL and Post parameter
        'odds': Dict of Umaren Odds {馬連組み合わせ : オッズ}
        'vote': 全体投票情報
            'umaren': 枠連投票数
            'total': 単勝 + 複勝投票数
    """

class OddsParserExacta(OddsParserBracket):
    list_class_tag = 'umatan_list'
    # parse_content output
    """ Parse content and return odds exacta info if exist
    :param soup:
    :return: Array of Dict of Odds Exacta
        'links': URLs
            'win': 単勝・複勝 URL and Post parameter
            'umaren': 馬連 URL and Post parameter
            'wide': 馬連 URL and Post parameter
            'umatan': 馬連 URL and Post parameter
            'trio': 馬連 URL and Post parameter
            'tierce': 馬連 URL and Post parameter
        'odds': Dict of Umatan Odds {馬連組み合わせ : オッズ}
        'vote': 全体投票情報
            'umatan': 枠連投票数
            'total': 単勝 + 複勝投票数
    """


class OddsParserWide(OddsParser):
    def parse_odds_content(self, soup_area):
        soup_uls = soup_area.find_all('ul', attrs={'class': 'wide_list'})

        odds = {}

        for soup_ul in soup_uls:
            soup_lis = soup_ul.find_all('li')

            for soup_li in soup_lis:
                soup_table = soup_li.find('table')
                tag_1 = soup_table.find('caption').getText().strip()
                soup_trs = soup_li.find_all('tr')
                for soup_tr in soup_trs:
                    th = soup_tr.find('th').getText().strip()
                    odds[tag_1 + '-' + th] = {}
                    soup_td = soup_tr.find('td')

                    soup_min = soup_td.find('span', attrs={'class': 'min'})
                    if soup_min is None:
                        val = soup_td.getText().strip()
                        odds[tag_1 + '-' + th]['min'] = val
                        odds[tag_1 + '-' + th]['max'] = val
                        continue

                    min = soup_min.getText().strip()
                    if min == '':
                        continue
                    else:
                        try:
                            min_val = float(min)
                        except ValueError:
                            logger.debug('Float Convertion Error: ' + soup_tr.find('th').getText().strip())
                            min_val = min

                    odds[tag_1 + '-' + th]['min'] = min_val

                    max = soup_td.find('span', attrs={'class': 'max'}).getText().strip()
                    if max == '':
                        continue
                    else:
                        try:
                            max_val = float(max)
                        except ValueError:
                            logger.debug('Float Convertion Error: ' + soup_tr.find('th').getText().strip())
                            max_val = max

                    odds[tag_1 + '-' + th]['max'] = max_val


        return odds

        # parse_content output
        """ Parse content and return odds wide info if exist
        :param soup:
        :return: Array of Dict of Odds Wide
            'links': URLs
                'win': 単勝・複勝 URL and Post parameter
                'umaren': 馬連 URL and Post parameter
                'wide': 馬連 URL and Post parameter
                'umatan': 馬連 URL and Post parameter
                'trio': 馬連 URL and Post parameter
                'tierce': 馬連 URL and Post parameter
            'odds': Dict of Umatan Odds {馬連組み合わせ : {
                        'min': 最低オッズ
                        'max': 最大オッズ
                    }
            'vote': 全体投票情報
                'wide': 枠連投票数
                'total': 単勝 + 複勝投票数
        """


class OddsParserTrio(OddsParser):
    def parse_odds_content(self, soup_area):
        odds = {}

        soup_odds_list = soup_area.find('div', attrs={'id': 'odds_list'})
        soup_fuku3_unit_list = soup_odds_list.find_all('div', attrs={'class': 'fuku3_unit'})
        for soup_fuku3_unit in soup_fuku3_unit_list:
            soup_uls = soup_fuku3_unit.find_all('ul', attrs={'class': 'fuku3_list'})
            for soup_ul in soup_uls:
                soup_lis = soup_ul.find_all('li')
                for soup_li in soup_lis:
                    soup_caption = soup_li.find('caption')
                    soup_trs = soup_li.find_all('tr')
                    for soup_tr in soup_trs:
                        th = soup_tr.find('th').getText().strip()
                        td = soup_tr.find('td').getText().strip()
                        tag = '{}-{}'.format(soup_caption.getText().strip(), th)
                        if td != '取消':
                            try:
                                odds_val = float(td)
                                odds[tag] = odds_val
                            except ValueError:
                                logger.error('Failed to conver odds ' + td)
                        else:
                            odds[tag] = td

                        #logger.debug('{}-{} => {}'.format(soup_caption.getText().strip(), th, td))

        return odds

    # parse_content output
    """ Parse content and return odds trio info if exist
    :param soup:
    :return: Array of Dict of Odds Trio
        'links': URLs
            'win': 単勝・複勝 URL and Post parameter
            'umaren': 馬連 URL and Post parameter
            'wide': 馬連 URL and Post parameter
            'umatan': 馬連 URL and Post parameter
            'trio': 馬連 URL and Post parameter
            'tierce': 馬連 URL and Post parameter
        'odds': Dict of Trio Odds {三連複組み合わせ : オッズ
        'vote': 全体投票情報
            'trio': 三連複投票数
            'total': 単勝 + 複勝投票数
    """


class OddsParserTierce(OddsParser):
    def parse_odds_content(self, soup_area):
        odds = {}

        soup_odds_list = soup_area.find('div', attrs={'id': 'odds_list'})
        soup_fuku3_unit_list = soup_odds_list.find_all('div', attrs={'class': 'tan3_unit'})

        for soup_fuku3_unit in soup_fuku3_unit_list:
            soup_lis = soup_fuku3_unit.find_all('li')
            for soup_li in soup_lis:
                soup_divs = soup_li.find_all('div', attrs={'class': 'num'})
                if len(soup_divs) != 2:
                    logger.error('Not enough pairs')
                    continue

                soup_trs = soup_li.find_all('tr')
                for soup_tr in soup_trs:
                    th = soup_tr.find('th').getText().strip()
                    td = soup_tr.find('td').getText().strip()
                    if td == '':
                        continue

                    tag = '{}-{}-{}'.format(soup_divs[0].getText().strip(), soup_divs[1].getText().strip(), th)
                    if td != '取消':
                        try:
                            odds_val = float(td)
                            odds[tag] = odds_val
                        except ValueError:
                            logger.error('Failed to conver odds ' + td)
                    else:
                        odds[tag] = td

        return odds

    # parse_content output
    """ Parse content and return odds tierce info if exist
    :param soup:
    :return: Array of Dict of Odds Tierce
        'links': URLs
            'win': 単勝・複勝 URL and Post parameter
            'umaren': 馬連 URL and Post parameter
            'wide': 馬連 URL and Post parameter
            'umatan': 馬連 URL and Post parameter
            'trio': 馬連 URL and Post parameter
            'tierce': 馬連 URL and Post parameter
        'odds': Dict of Trio Odds {三連単組み合わせ: オッズ}
        'vote': 全体投票情報
            'tierce': 三連単投票数
            'total': 単勝 + 複勝投票数
    """