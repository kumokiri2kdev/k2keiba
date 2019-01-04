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
    def parse_odds_content(self, soup_area):
        soup_ul = soup_area.find('ul', attrs={'class': 'umaren_list mt15'})
        soup_lis = soup_ul.find_all('li')

        odds = {}
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

