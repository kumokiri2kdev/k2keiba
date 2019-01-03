""" JRA Odds Page Parser """
import logging
import re

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

class OddsParserWin(parser.ParserPost):
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


    def parse_content(self, soup):
        odds = {}
        soup_area = soup.find('div', attrs={'id': 'contentsBody'})

        links = self.parse_odds_links(soup_area)

        odds['links'] = links

        soup_table = soup_area.find('table', attrs={'class': 'tanpuku'})
        horses = self.parse_odds_winplace(soup_table)

        odds['horses'] = horses

        soup_vote = soup_area.find('div', attrs={'id': 'votes'})
        if soup_vote is not None:
            vote = self.parse_odds_vote(soup_vote)
            odds['vote'] = vote

        # ToDo : Observe running odds
        soup_reflresh = soup_area.find('div', attrs={'class': 'refresh_line'})
        if soup_reflresh:
            odds['refresh'] = util.Util.trim_clean(soup_reflresh.getText())

        return odds