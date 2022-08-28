""" JRA Uma Page Parser """
import logging

from . import util
from . import parser


class ParserUma(parser.ParserPost):

    def filter_tables(self, tbls):
        ret_tbls = {}

        for (i, tbl) in enumerate(tbls):
            div = tbl.find('div', attrs={'class': 'main'})
            if div:
                tag = util.Util.trim_clean(div.get_text())
                if tag == '出走レース':
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
                    #     params = util.Util.parse_func_params(anchor['onclick'])
                    #     ret_race['params'] = params
                        ret_race['params'] = util.Util.format_params2(anchor['href'])
            try:
                ret_race['date'] = util.Util.parse_date_to_int(ret_race['date'])
            except ValueError:
                return {}

            if 'place' in ret_race and ret_race['place'] == '':
                ret_race_ex = {}
                ret_race_ex['date'] = ret_race['date']
                ret_race_ex['info'] = ret_race['name']
                ret_race_ex['type'] = 'info'
                ret.append(ret_race_ex)
            else:
                race = {}
                for key in ret_race:
                    if ret_race[key] is not '':
                        race[key] = ret_race[key]

                race['type'] = 'race'
                ret.append(race)

        return ret

    def parse_profile(self, profile):
        soup_lis = profile.find_all('li')
        ret_profile = {}
        tag_table = {
            '父': 'father',
            '母': 'mother',
            '母の父': 'bmr',
            '母の母': 'mother_of_mother',
            '性別': 'sex',
            '馬主': 'owner',
            '馬齢': 'age',
            '調教師': 'trainer',
            '生年月日': 'birthday',
            '生産牧場': 'breeding_farm',
            '毛色': 'hair',
            '産地': 'breeding_center',
            '馬名意味': 'origin_of_name'
        }

        for soup_li in soup_lis:
            soup_dt = soup_li.find('dt')
            tag = util.Util.trim_clean(soup_dt.get_text())
            soup_dd = soup_li.find('dd')
            value = util.Util.trim_clean(soup_dd.get_text())

            if tag in tag_table:
                ret_profile[tag_table[tag]] = value


        return ret_profile

    def parse_basic(self, spans):
        ret_basic = {}
        for span in spans:
            opt_span = span.find('span', attrs={'class': 'opt'})
            if opt_span is not None:
                spans_to_be_removed = span.find_all('span')
                for span_to_be_removed in spans_to_be_removed:
                    span_to_be_removed.extract()

                ret_basic['name'] = span.get_text()
                break

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
                'father': 父
                'mother': 母
                'bmr': 母の父
                'mother_of_mother': 母の母
                'sex': 性別
                'owner': 馬主
                'age': 馬齢
                'trainer': 調教師
                'bmr': 母の父
                'birthday': 生年月日
                'breeding_farm': 生産牧場
                'hair': 毛色
                'breeding_center': 産地
                'origin_of_name': 馬名意味
        """

        parsed_data = {}

        spans = soup.find_all('span', attrs={'class': 'txt'})
        parsed_data['basic'] = self.parse_basic(spans)

        soup_profile = soup.find('div', attrs={'class': 'profile'})
        parsed_data['profile'] = self.parse_profile(soup_profile)

        tbls = soup.find_all("table")
        filtered_tbls = self.filter_tables(tbls)

        if 'races' in filtered_tbls:
            parsed_race = self.parse_races(filtered_tbls['races'])
            parsed_data['races'] = parsed_race


        return parsed_data

