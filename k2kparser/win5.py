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
        ret = {}

        ret['course'] = element.find('span', attrs={'class': 'rc'}).get_text().strip()
        ret['id'] = element.find('span', attrs={'class': 'num'}).get_text().strip()
        ret['name'] = element.find('span', attrs={'class': 'name'}).get_text().strip()

        anchor = element.find('a')
        params = util.Util.parse_func_params(anchor['onclick'])

        ret['url'] = params

        return ret

    @classmethod
    def race_ninki_filter(cls, element):
        ninki = element.get_text().strip()
        if ninki == '':
            return None

        nink = ninki.split('¥n')
        return int(ninki[0].replace('番人気', ''))

    @classmethod
    def race_remaining_filter(cls, element):
        remaining = element.get_text().strip()
        if remaining == '':
            return None

        return int(remaining.replace('票', '').replace(',', ''))

    @classmethod
    def race_winner_filter(cls, element):
        ret = {}
        num = element.find('div', attrs={'class': 'num'})
        if num is None:
            return

        ret['number'] = int(num.get_text())

        winner = element.find('div', attrs={'class': 'name'})
        anchor = winner.find('a')
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
    def parse_win5_data_unit(cls, soup_content_body, ret):
        soup_data_units = soup_content_body.find_all('div', attrs={'class': 'win5_data_unit'})

        for soup_data_unit in soup_data_units:
            soup_cap = soup_data_unit.find('div', attrs={'class': 'cap'})
            tag = soup_cap.get_text().strip()
            soup_main = soup_data_unit.find('div', attrs={'class': 'main'})
            if tag == 'キャリーオーバー！':
                if soup_main != None:
                    try:
                        ret['carried_over'] = int(soup_main.get_text().replace('円', '').replace(',', ''))
                    except:
                        logger.debug('Carry over here, but failed to get information.')
            elif tag == '次回へのキャリーオーバー':
                if soup_main != None:
                    try:
                        ret['carry_over'] = int(soup_main.get_text().replace('円', '').replace(',', ''))
                    except:
                        logger.debug('Carry over here, but failed to get information.')
            elif tag == '発売票数':
                if soup_main != None:
                    try:
                        ret['bets'] = int(soup_main.get_text().replace('票', '').replace(',', ''))
                    except ValueError:
                        logger.debug('Total Bet is empty ? : ' + soup_main.get_text())
            elif tag == '発売金額':
                if soup_main != None:
                    try:
                        ret['bet_price'] = int(soup_main.get_text().replace('円', '').replace(',', ''))
                    except ValueError:
                        logger.debug('Total Bet Price is empty ? : ' + soup_main.get_text())

            elif tag == '的中馬番':
                if soup_main != None:
                    indexes = soup_main.get_text().strip()
                    if indexes != '':
                        ret['indexes'] = indexes
            elif tag == '払戻金':
                if soup_main != None:
                    try:
                        pay_back = soup_main.get_text().strip()
                        if pay_back != '':
                            ret['pay_back'] = int(pay_back.replace('円', '').replace(',', ''))
                    except:
                        logger.info('Pay Back here, but failed to get information.')
            elif tag == '的中票数':
                if soup_main != None:
                    try:
                        remaining = soup_main.get_text().strip()
                        if remaining != '':
                            ret['remaining'] = int(remaining.replace('票', '').replace(',', ''))
                    except:
                        logger.info('Remaining here, but failed to get information.')



    @classmethod
    def parse_win5_result(cls, win5list, ret):
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
                    soup_siblings = soup_th.find_next_siblings('td')
                elif th_tag in 'レース':
                    json_tag = 'race'
                    filter_func = ParserWin5Filter.race_race_filter
                    soup_siblings = soup_th.find_next_siblings('td')
                elif th_tag in '勝馬':
                    json_tag = 'winner'
                    filter_func = ParserWin5Filter.race_winner_filter
                    soup_siblings = soup_th.find_next_siblings('td')
                    #soup_siblings = [soup_siblings[0], soup_siblings[2],
                    #                 soup_siblings[4], soup_siblings[6], soup_siblings[8]]
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

        soup_content_body = soup.find('div', attrs={'id': 'contentsBody'})
        soup_date_str = soup_content_body.find('div', attrs={'class': 'main'})
        if soup_date_str != None:
            date, weekday = util.Util.parser_date(soup_date_str.get_text())
            ret['date'] = date
            ret['weekday'] = weekday


        soup_div = soup_content_body.find('div', attrs={'class': 'opt'})
        soup_anchors = soup_div.find_all('a', attrs={'href': '#'})
        for soup_anchor in soup_anchors:
            soup_i = soup_anchor.find('i')
            if soup_i is not None:
                print(soup_i['class'])
                if 'fa-chevron-circle-left' in soup_i['class']:
                    params = util.Util.parse_func_params(soup_anchor['onclick'])
                    ret['prev_url'] = params
                elif 'fa-chevron-circle-right' in soup_i['class']:
                    params = util.Util.parse_func_params(soup_anchor['onclick'])
                    ret['next_url'] = params

        soup_result = soup.find('div', attrs={'class': 'result_detail'})
        soup_table = soup_result.find('table')
        self.parse_win5_result(soup_table, ret)

        #soup_data_units = soup_content_body.find_all('div', attrs={'class': 'win5_data_unit'})
        self.parse_win5_data_unit(soup_content_body, ret)

        # soup_win5lists = soup.find_all('table', attrs={'class': 'win5List'})
        # win5list_parse_funcs = [
        #     self.parse_win5list_0,
        #     self.parse_win5list_1,
        #     self.parse_win5list_2,
        #     self.parse_win5list_3
        # ]
        #
        # for func, list in zip(win5list_parse_funcs, soup_win5lists[-5:]):
        #     func(list, ret)

        return ret
