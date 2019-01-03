""" JRA Uma Page Parser """
import logging

from . import util
from . import parser


class ParserUma(parser.ParserPost):

    def filter_tables(self, tbls):
        ret_tbls = {}

        for (i, tbl) in enumerate(tbls):
            td = tbl.find('td')
            if td:
                tag = util.Util.trim_clean(td.get_text())
                if tag == '【出走レース】':
                    ret_tbls['races'] = tbl
                elif tag == '【プロフィール】':
                    ret_tbls['profile'] = tbl
                    ret_tbls['basic'] = tbls[i - 1]

        return ret_tbls

    def parse_races(self, races):
        tags = ['date', 'place', 'name', 'candd', 'condition',
                'number', 'ninki', 'rank', 'jokey', 'hande', 'weight',
                'time', 'winner']

        trs = races.find_all('tr')[1::]
        ret = []

        for tr in trs:
            if tr.has_attr('class') and 'gray12_h' in tr['class']:
                continue

            ret_race = {}
            tds = tr.find_all('td')

            for tag, td in zip(tags, tds):
                ret_race[tag] = util.Util.trim_clean(td.get_text())
                if tag == 'name':
                    anchor = td.find("a")
                    if anchor:
                        params = util.Util.parse_func_params(anchor['onclick'])
                        ret_race['params'] = params

            try:
                ret_race['date'] = int(ret_race['date'].replace('.', ''))
            except ValueError:
                return {}

            if 'place' in ret_race and ret_race['place'] == '':
                ret_race_ex = {}
                ret_race_ex['date'] = ret_race['date']
                ret_race_ex['info'] = ret_race['name']
                ret_race_ex['type'] = 'info'
                ret.append(ret_race_ex)
            else:
                ret_race['type'] = 'race'
                ret.append(ret_race)

        return ret

    def parse_profile(self, profile):
        soup_trs = profile.find_all('tr')
        ret_profile = {}

        for soup_tr in soup_trs:
            soup_tds = soup_tr.find_all('td')

            for i in range(0, len(soup_tds) - len(soup_tds) % 2, 2):
                if len(soup_tds) > i:
                    tag = util.Util.trim_clean(soup_tds[i].get_text())
                if len(soup_tds) > (i + 1):
                    value = util.Util.trim_clean(soup_tds[i + 1].get_text())

                if 'tag' in locals() and 'value' in locals():
                    ret_profile[tag] = value
                    del (tag)
                    del (value)

        return ret_profile

    def parse_basic(self, basic):
        ret_basic = {}

        soup_td = basic.find('td')
        soup_span = soup_td.find('span')
        ret_basic['name'] = util.Util.trim_clean(soup_span.get_text())

        return ret_basic

    def parse_content(self, soup):
        """ Parse content and return parameters if exist
        :param soup:
        :return: Array of Dict of Horse Information
            'basic':
                'name': 馬名
            'races': Array of races
                'date': 日付
                'place': 競馬場
                'name': レース名
                'params': URL and Post parameter of the race
                'candd': コースと距離
                'condition': 馬場状態
                'number': 頭数
                'ninki': 人気
                'rank': 着順
                'jokey': 騎手
                'hande': 斤量
                'weight': 馬体重
                'time': 走破時計
                'winner': 勝ち馬
                'type': 'race'
            'profile': プロフィール
                '父': 父
                '性別': 性別
                '馬主': 馬主
                '母': 母
                '馬齢': 馬齢
                '調教師': 調教師
                '母の父': 母の父
                '生年月日': 生年月日
                '生産牧場': 生産牧場
                '母の母': 母の母
                '毛色': 毛色
                '産地': 産地
                '馬名意味': 馬名意味
        """
        tbls = soup.find_all("table")
        filtered_tbls = self.filter_tables(tbls)

        parsed_data = {}

        if 'basic' in filtered_tbls:
            parsed_basic = self.parse_basic(filtered_tbls['basic'])
            parsed_data['basic'] = parsed_basic

        if 'races' in filtered_tbls:
            parsed_race = self.parse_races(filtered_tbls['races'])
            parsed_data['races'] = parsed_race

        if 'profile' in filtered_tbls:
            parsed_profile = self.parse_profile(filtered_tbls['profile'])
            parsed_data['profile'] = parsed_profile

        return parsed_data

