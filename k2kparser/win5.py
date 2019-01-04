import logging
import re

from . import util
from . import parser


logger = logging.getLogger(__name__)

class ParserWin5Filter(parser.ParserPost):
    @classmethod
    def race_index_filter(cls, element):
        return int(element.get_text().replace('レース目', ''))

    @classmethod
    def race_departurer_filter(cls, element):
        return element.get_text().strip()

    @classmethod
    def race_race_filter(cls, element):
        text = element.get_text().strip()

        race_info = text.split('\n')
        ret = {}
        ret['id'] = race_info[0]
        ret['name'] = race_info[1]

        anchor = element.find('a')
        params = util.Util.parse_func_params(anchor['onclick'])

        ret['url'] = params

        return ret

    @classmethod
    def race_ninki_filter(cls, element):
        ninki = element.get_text().strip()
        if ninki == '':
            return None

        return int(ninki.replace('番人気', ''))

    @classmethod
    def race_remaining_filter(cls, element):
        remaining = element.get_text().strip()
        if remaining == '':
            return None

        return int(remaining.replace('票', '').replace(',', ''))

    @classmethod
    def race_winner_filter(cls, element):
        ret = {}
        num = element.find('td')
        if num is None:
            return

        ret['number'] = int(num.get_text())
        anchor = element.find_next_sibling().find('a')
        params = util.Util.parse_func_params(anchor['onclick'])
        horse = {}
        horse['url'] = params
        horse['name'] = anchor.get_text()

        ret['horse'] = horse

        return ret

class ParserWin5Kaisai(parser.ParserPost):
    def __init__(self, path, param):
        super().__init__(path, param)

    @classmethod
    def parse_win5list_0(cls, win5list, ret):
        soup_trs = win5list.find_all('tr')
        for soup_tr in soup_trs:
            soup_th = soup_tr.find('th')
            if soup_th != None and soup_th.get_text() == 'キャリーオーバー！':
                soup_td = soup_tr.find('td')
                if soup_td != None:
                    try:
                        ret['carry_over'] = int(soup_td.get_text().replace('円', '').replace(',', ''))
                    except:
                        logger.debug('Carry over here, but failed to get information.')

    @classmethod
    def parse_win5list_1(cls, win5list, ret):
        soup_trs = win5list.find_all('tr')
        for soup_tr in soup_trs:
            soup_th = soup_tr.find('th')
            if soup_th != None:
                tag = soup_th.get_text()
                if '発売票数' in tag:
                    soup_td = soup_tr.find('td')
                    if soup_td != None:
                        try:
                            ret['bets'] = int(soup_td.get_text().replace('票', '').replace(',', ''))
                        except ValueError:
                            logger.debug('Total Bet is empty ? : ' + soup_td.get_text())
                elif '発売金額' in tag:
                    soup_td = soup_tr.find('td')
                    if soup_td != None:
                        try:
                            ret['bet_price'] = int(soup_td.get_text().replace('円', '').replace(',', ''))
                        except ValueError:
                            logger.debug('Total Bet Price is empty ? : ' + soup_td.get_text())

    @classmethod
    def parse_win5list_2(cls, win5list, ret):
        soup_trs = win5list.find_all('tr')

        ret['list'] = [{} for i in range(5)]
        for i, soup_tr in enumerate(soup_trs):
            soup_th = soup_tr.find('th')
            if soup_th:
                th_tag = soup_th.get_text()
                if th_tag in ' ':
                    json_tag = 'index'
                    filter_func = ParserWin5Filter.race_index_filter
                    soup_siblings = soup_th.find_next_siblings('th')
                elif th_tag in '発走時刻':
                    json_tag = 'departure'
                    filter_func = ParserWin5Filter.race_departurer_filter
                    soup_siblings = soup_th.find_next_siblings('th')
                elif th_tag in 'レース':
                    json_tag = 'race'
                    filter_func = ParserWin5Filter.race_race_filter
                    soup_siblings = soup_th.find_next_siblings('th')
                elif th_tag in '勝馬':
                    json_tag = 'winner'
                    filter_func = ParserWin5Filter.race_winner_filter
                    soup_siblings = soup_th.find_next_siblings('td')
                    soup_siblings = [soup_siblings[0], soup_siblings[2],
                                     soup_siblings[4], soup_siblings[6], soup_siblings[8]]
                elif th_tag in '残り票数':
                    json_tag = 'remaining'
                    filter_func = ParserWin5Filter.race_remaining_filter
                    soup_siblings = soup_th.find_next_siblings('td')
                elif th_tag in '単勝人気':
                    json_tag = 'ninki'
                    filter_func = ParserWin5Filter.race_ninki_filter
                    soup_siblings = soup_th.find_next_siblings('td')
                else:
                    continue

                for i, soup_sibling in enumerate(soup_siblings):
                    info = filter_func(soup_sibling)
                    if info is not None:
                        ret['list'][i][json_tag] = info

    @classmethod
    def parse_win5list_3(cls, win5list, ret):
        soup_trs = win5list.find_all('tr')

        for soup_tr in soup_trs:
            soup_th = soup_tr.find('th')
            if soup_th != None:
                tag = soup_th.get_text()
                if '的中馬番' in tag:
                    soup_td = soup_tr.find('td')
                    if soup_td != None:
                        indexes = soup_td.get_text().strip()
                        if indexes != '':
                            ret['indexes'] = indexes
                elif '払戻金' in tag:
                    soup_td = soup_tr.find('td')
                    if soup_td != None:
                        try:
                            pay_back = soup_td.get_text().strip()
                            if pay_back != '':
                                ret['pay_back'] = int(pay_back.replace('円', '').replace(',', ''))
                        except:
                            logger.info('Pay Back here, but failed to get information.')
                elif '的中票数' in tag:
                    soup_td = soup_tr.find('td')
                    if soup_td != None:
                        try:
                            remaining = soup_td.get_text().strip()
                            if remaining != '':
                                ret['remaining'] = int(remaining.replace('票', '').replace(',', ''))
                        except:
                            logger.info('Remaining here, but failed to get information.')


    def parse_content(self, soup):
        """ Parse content and return win5 kaisai info if exist
        :param soup:
        :return: Dict of win5 kaisai info
            'date': 日付
            'weekday': 曜日
            'prev_url': 前回 URL
            'next_url': 次回 URL
            'carry_over': キャリーオーバー数（未発生時は 0）
            'bets':
            'kaisai': Array of Kaisai information
                'index': 開催回数
                'day': 開催日（何日目）
                'place': 競馬場
                'params': URL and Post parameter
                'bets': 投票数
                'bet_price': 投票金額
                'list': Array of races
                    'index': WIN5 レース番号
                    'departure': 発走時刻
                    'race': レース情報
                        'id': 東京10R'
                        'name': レース名
                        'url': URL and Post parameter
                        'winner': 勝ち馬
                            'number': 馬番
                            'horse': 馬情報
                                'name': 馬名
                                'url': URL and Post parameter
                        'ninki': 人気順
                        'remaining': 残票数
        """
        ret = {}

        soup_date_str = soup.find('td', attrs={'class': 'header3'})
        if soup_date_str != None:
            date, weekday = util.Util.parser_date(soup_date_str.get_text())
            ret['date'] = date
            ret['weekday'] = weekday

            soup_anchors = soup.find_all('a', attrs={'href': '#'})
        for soup_anchor in soup_anchors:
            text = soup_anchor.get_text()
            if re.search(r'[0-9]{4}年[0-9]*月[0-9]*日.*→', text) != None:
                params = util.Util.parse_func_params(soup_anchor['onclick'])
                ret['next_url'] = params
            elif re.search(r'←[0-9]{4}年[0-9]*月[0-9]*日', text) != None:
                params = util.Util.parse_func_params(soup_anchor['onclick'])
                ret['prev_url'] = params

        soup_win5lists = soup.find_all('table', attrs={'class': 'win5List'})
        win5list_parse_funcs = [
            self.parse_win5list_0,
            self.parse_win5list_1,
            self.parse_win5list_2,
            self.parse_win5list_3
        ]

        for func, list in zip(win5list_parse_funcs, soup_win5lists[-5:]):
            func(list, ret)

        return ret
