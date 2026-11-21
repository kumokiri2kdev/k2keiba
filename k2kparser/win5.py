""" JRA WIN5 Page Parser

Output keys follow docs/naming.md.
"""
import logging

from . import util
from . import parser
from .den import _onclick_link, _href_link


logger = logging.getLogger(__name__)


class ParserWin5Filter:
    """ Converters for each row of the WIN5 result table. Each returns a dict merged into the leg. """
    @classmethod
    def race_index_filter(cls, element):
        return {'leg': util.parse_int(element.get_text())}

    @classmethod
    def race_departure_filter(cls, element):
        departure = util.to_hhmm(element.get_text())
        return {'departure': departure} if departure else {}

    @classmethod
    def race_race_filter(cls, element):
        ret = {}
        soup_rc = element.find('span', attrs={'class': 'rc'})
        if soup_rc is not None:
            ret['racecourse'] = soup_rc.get_text().strip()
        soup_num = element.find('span', attrs={'class': 'num'})
        if soup_num is not None:
            ret['race_num'] = util.parse_int(soup_num.get_text())
        soup_name = element.find('span', attrs={'class': 'name'})
        if soup_name is not None:
            ret['name'] = soup_name.get_text().strip()
        link = _href_link(element.find('a'))
        if link:
            ret['link'] = link
        return ret

    @classmethod
    def race_popularity_filter(cls, element):
        popularity = util.parse_int(element.get_text())
        return {'popularity': popularity} if popularity is not None else {}

    @classmethod
    def race_remaining_filter(cls, element):
        remaining = util.parse_int(element.get_text())
        return {'remaining_votes': remaining} if remaining is not None else {}

    @classmethod
    def race_winner_filter(cls, element):
        soup_num = element.find('div', attrs={'class': 'num'})
        if soup_num is None:
            return {}
        winner = {'horse_num': util.parse_int(soup_num.get_text())}
        soup_anchor = element.find('div', attrs={'class': 'name'}).find('a')
        if soup_anchor is not None:
            winner['name'] = soup_anchor.get_text().strip()
            link = _href_link(soup_anchor)
            if link:
                winner['link'] = link
        return {'winner': winner}


# 結果表の行見出し -> (変換関数, 値のセルのタグ)
_ROW_FILTERS = (
    ('発走時刻', ParserWin5Filter.race_departure_filter, 'td'),
    ('レース', ParserWin5Filter.race_race_filter, 'td'),
    ('勝馬', ParserWin5Filter.race_winner_filter, 'td'),
    ('残り票数', ParserWin5Filter.race_remaining_filter, 'td'),
    ('単勝人気', ParserWin5Filter.race_popularity_filter, 'td'),
)

# 集計欄の見出し -> (キー, 単位)
_DATA_UNITS = {
    'キャリーオーバー！': 'carryover_in',
    '次回へのキャリーオーバー': 'carryover_out',
    '発売票数': 'votes',
    '発売金額': 'sales',
    '払戻金': 'payout',
    '的中票数': 'winning_votes',
}


class ParserWin5Kaisai(parser.ParserPost):
    def __init__(self, path, param, **kwargs):
        super().__init__(path, param, **kwargs)

    @classmethod
    def parse_win5_result(cls, soup_table, ret):
        races = [{} for _ in range(5)]
        for soup_tr in soup_table.find_all('tr'):
            soup_th = soup_tr.find('th')
            if soup_th is None:
                continue
            th_tag = soup_th.get_text().strip()
            if th_tag == '':
                # Header row: '1レース目', '2レース目', ...
                filter_func, soup_cells = ParserWin5Filter.race_index_filter, soup_th.find_next_siblings('th')
            else:
                for tag, func, cell in _ROW_FILTERS:
                    if th_tag == tag:
                        filter_func, soup_cells = func, soup_th.find_next_siblings(cell)
                        break
                else:
                    continue

            for i, soup_cell in enumerate(soup_cells[:5]):
                races[i].update(filter_func(soup_cell))

        ret['races'] = races

    @classmethod
    def parse_win5_closing_time(cls, soup_content_body, ret):
        soup_closing = soup_content_body.find('div', attrs={'class': 'closing_time'})
        if soup_closing is None:
            return
        for side, key in (('left', 'closing_time_pat'), ('right', 'closing_time_direct')):
            soup_side = soup_closing.find('div', attrs={'class': side})
            soup_dd = soup_side.find('dd') if soup_side else None
            if soup_dd is not None:
                closing_time = util.to_hhmm(soup_dd.get_text())
                if closing_time:
                    ret[key] = closing_time

    @classmethod
    def parse_win5_data_unit(cls, soup_content_body, ret):
        for soup_unit in soup_content_body.find_all('div', attrs={'class': 'win5_data_unit'}):
            tag = soup_unit.find('div', attrs={'class': 'cap'}).get_text().strip()
            soup_main = soup_unit.find('div', attrs={'class': 'main'})
            if soup_main is None:
                continue
            text = soup_main.get_text().strip()
            if tag == '的中馬番':
                if text != '':
                    ret['winning_combination'] = text
            elif tag in _DATA_UNITS:
                value = util.parse_int(text)
                if value is not None:
                    ret[_DATA_UNITS[tag]] = value

    def parse_content(self, soup):
        """ WIN5（1開催日）
        :return: dict
            'date', 'weekday'
            'prev_link', 'next_link': 前回・次回の WIN5
            'closing_time_pat', 'closing_time_direct': 締切時刻（'HH:MM'）
            'races': list of 5 dict
                'leg': WIN5 の何レース目か（1〜5）
                'departure', 'racecourse', 'race_num', 'name', 'link'
                'winner': {'horse_num', 'name', 'link'}  (結果確定後)
                'popularity': 勝ち馬の単勝人気  (結果確定後)
                'remaining_votes': 残り票数  (結果確定後)
            'votes': 発売票数, 'sales': 発売金額（円）
            'carryover_in': 前回からのキャリーオーバー（円）
            'carryover_out': 次回へのキャリーオーバー（円）
            'winning_combination': 的中馬番（'6-10-13-1-2'）
            'payout': 払戻金（円）, 'winning_votes': 的中票数
        """
        ret = {}

        soup_content_body = soup.find('div', attrs={'id': 'contentsBody'})
        soup_date = soup_content_body.find('div', attrs={'class': 'main'})
        if soup_date is not None:
            ret['date'] = util.to_iso_date(soup_date.get_text())
            weekday = util.parse_weekday(soup_date.get_text())
            if weekday:
                ret['weekday'] = weekday

        soup_opt = soup_content_body.find('div', attrs={'class': 'opt'})
        if soup_opt is not None:
            for soup_anchor in soup_opt.find_all('a', attrs={'href': '#'}):
                soup_i = soup_anchor.find('i')
                if soup_i is None:
                    continue
                if 'fa-chevron-circle-left' in soup_i['class']:
                    link = _onclick_link(soup_anchor)
                    if link:
                        ret['prev_link'] = link
                elif 'fa-chevron-circle-right' in soup_i['class']:
                    link = _onclick_link(soup_anchor)
                    if link:
                        ret['next_link'] = link

        self.parse_win5_closing_time(soup_content_body, ret)

        soup_result = soup.find('div', attrs={'class': 'result_detail'})
        self.parse_win5_result(soup_result.find('table'), ret)

        self.parse_win5_data_unit(soup_content_body, ret)

        return ret
