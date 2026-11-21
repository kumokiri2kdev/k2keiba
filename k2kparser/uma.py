""" JRA Uma (競走馬) Page Parser

Output keys follow docs/naming.md.
"""
import logging
import re

from . import util
from . import parser
from .den import _onclick_link, _href_link

logger = logging.getLogger(__name__)

# プロフィールの見出し -> キー
PROFILE_TABLE = {
    '父': 'sire',
    '母': 'dam',
    '母の父': 'broodmare_sire',
    '母の母': 'dam_dam',
    '性別': 'sex',
    '馬主名': 'owner',
    '馬主': 'owner',
    '馬齢': 'age',
    '調教師名': 'trainer',
    '調教師': 'trainer',
    '生年月日': 'birthday',
    '生産牧場': 'breeding_farm',
    '毛色': 'coat',
    '産地': 'birthplace',
    '馬名意味': 'name_meaning',
    '取引市場': 'market',
}


class ParserUma(parser.ParserPost):

    # ---- 成績表: 列は見出しの class 名で判別する（列の追加・並び替えに強くするため） ----

    @staticmethod
    def _col_date(td, race):
        race['date'] = util.to_iso_date(td.get_text())

    @staticmethod
    def _col_course(td, race):
        text = util.Util.trim_clean(td.get_text())
        if text:
            race['racecourse'] = text

    @staticmethod
    def _col_race(td, race):
        soup_grade = td.find('span', attrs={'class': 'grade_icon'})
        if soup_grade is not None:
            if soup_grade.find('img') is not None:
                race['grade'] = soup_grade.find('img')['alt']
            soup_grade.extract()
        race['name'] = util.Util.trim_clean(td.get_text())
        link = _href_link(td.find('a'))
        if link:
            race['link'] = link

    @staticmethod
    def _col_dist(td, race):
        text = util.Util.trim_clean(td.get_text())     # 'ダ1700', '芝2000', '障3000'
        surface = util.parse_surface(text)
        if surface:
            race['surface'] = surface
        distance = util.parse_int(text)
        if distance is not None:
            race['distance'] = distance

    @staticmethod
    def _col_baba(td, race):
        text = util.Util.trim_clean(td.get_text())
        if text:
            race['track_condition'] = text

    @staticmethod
    def _col_int(key):
        def col(td, race):
            value = util.parse_int(td.get_text())
            if value is not None:
                race[key] = value
        return col

    @staticmethod
    def _col_place(td, race):
        text = util.Util.trim_clean(td.get_text())
        if text == '':
            return
        try:
            race['finish_position'] = int(text)
        except ValueError:
            race['finish_position'] = None
            race['finish_status'] = text

    @staticmethod
    def _col_jockey(td, race):
        name = util.Util.trim_clean(td.get_text())
        if name:
            race['jockey'] = util.person(name, _onclick_link(td.find('a')))

    @staticmethod
    def _col_hande(td, race):
        hande = util.parse_float(td.get_text())
        if hande is not None:
            race['hande'] = hande

    @staticmethod
    def _col_body_weight(td, race):
        text = util.Util.trim_clean(td.get_text())     # '472' or '472(-4)'
        if text == '' or not text[0].isdigit():
            return
        body_weight, body_weight_diff = util.Util.parse_weight(text)
        race['body_weight'] = body_weight
        if '(' in text:
            race['body_weight_diff'] = body_weight_diff

    @staticmethod
    def _col_time(td, race):
        text = util.Util.trim_clean(td.get_text())
        if text:
            try:
                race['finish_time'] = util.Util.parse_race_time(text)
            except util.UtilError:
                logger.debug('finish time parse error: ' + text)

    @staticmethod
    def _col_horse(td, race):
        text = util.Util.trim_clean(td.get_text())
        if text == '':
            return
        m = re.fullmatch(r'[(（](.*)[)）]', text)
        if m:
            race['runner_up'] = m.group(1)     # この馬が1着のときは2着馬が括弧付きで載る
        else:
            race['winner'] = text

    def _columns(self):
        return {
            'date': self._col_date,
            'course': self._col_course,
            'race': self._col_race,
            'dist': self._col_dist,
            'baba': self._col_baba,
            'num': self._col_int('horse_count'),
            'pop': self._col_int('popularity'),
            'place': self._col_place,
            'jockey': self._col_jockey,
            'weight': self._col_hande,
            'h_weight': self._col_body_weight,
            'time': self._col_time,
            'rate': self._col_int('rating'),
            'horse': self._col_horse,
        }

    def parse_races(self, soup_table):
        soup_trs = soup_table.find_all('tr')
        header = [th['class'][0] if th.has_attr('class') else '' for th in soup_trs[0].find_all('th')]
        columns = self._columns()
        unknown = [c for c in header if c not in columns]
        if unknown:
            logger.info('Unknown columns in race table: {}'.format(unknown))

        races = []
        for soup_tr in soup_trs[1:]:
            if soup_tr.has_attr('class') and 'gray12_h' in soup_tr['class']:
                continue
            soup_tds = soup_tr.find_all('td')
            if not soup_tds:
                continue

            race = {}
            cells = dict(zip(header, soup_tds))
            # 出走以外の行（登録抹消など）は場が空で、レース名の欄に説明が入る
            if 'course' in cells and util.Util.trim_clean(cells['course'].get_text()) == '':
                info = {'type': 'info'}
                try:
                    info['date'] = util.to_iso_date(cells['date'].get_text())
                except util.UtilError:
                    pass
                if 'race' in cells:
                    info['info'] = util.Util.trim_clean(cells['race'].get_text())
                races.append(info)
                continue

            race['type'] = 'race'
            for col, soup_td in cells.items():
                if col in columns:
                    try:
                        columns[col](soup_td, race)
                    except (util.UtilError, ValueError) as e:
                        logger.info('race table parse error ({}): {}'.format(col, e))
            races.append(race)

        return races

    # ---- プロフィール ----

    def parse_profile(self, soup_profile):
        profile = {}
        for soup_li in soup_profile.find_all('li'):
            soup_dt, soup_dd = soup_li.find('dt'), soup_li.find('dd')
            if soup_dt is None or soup_dd is None:
                continue
            tag = util.Util.trim_clean(soup_dt.get_text())
            if tag not in PROFILE_TABLE:
                continue
            key = PROFILE_TABLE[tag]

            for soup_sanku in soup_dd.find_all('span', attrs={'class': 'sanku'}):
                soup_sanku.extract()        # '産駒' link next to dam names
            value = util.Util.trim_clean(soup_dd.get_text())
            if value == '':
                continue

            if key == 'trainer':
                profile[key] = util.person(value, _onclick_link(soup_dd.find('a')))
            elif key == 'age':
                profile[key] = util.parse_int(value)
            elif key == 'birthday':
                profile[key] = util.to_iso_date(value)
            elif key == 'coat':
                profile[key] = util.normalize_coat(value)
            else:
                profile[key] = value
                if key in ('sire', 'dam', 'broodmare_sire', 'dam_dam'):
                    link = _href_link(soup_dd.find('a'))
                    if link:
                        profile[key + '_link'] = link

        return profile

    def parse_name(self, soup):
        for soup_span in soup.find_all('span', attrs={'class': 'txt'}):
            if soup_span.find('span', attrs={'class': 'opt'}) is not None:
                for soup_child in soup_span.find_all('span'):
                    soup_child.extract()
                return util.Util.trim_clean(soup_span.get_text())
        return None

    def parse_content(self, soup):
        """ 競走馬
        :return: dict
            'name': 馬名
            'profile': dict
                'sire', 'dam', 'broodmare_sire', 'dam_dam' (+ '<key>_link'),
                'sex', 'age', 'coat', 'birthday', 'owner', 'trainer',
                'breeding_farm', 'birthplace', 'name_meaning', 'market'
            'races': list of dict（新しい順）
                'type': 'race'
                    'date', 'racecourse', 'name', 'grade', 'link', 'surface', 'distance', 'track_condition',
                    'horse_count', 'popularity', 'finish_position', 'finish_status', 'jockey', 'hande',
                    'body_weight', 'finish_time', 'rating',
                    'winner': 1着馬（この馬が負けたとき） / 'runner_up': 2着馬（この馬が勝ったとき）
                'type': 'info'（出走以外の行）
                    'date', 'info'
        """
        ret = {}

        name = self.parse_name(soup)
        if name:
            ret['name'] = name

        soup_profile = soup.find('div', attrs={'class': 'profile'})
        if soup_profile is not None:
            ret['profile'] = self.parse_profile(soup_profile)

        for soup_table in soup.find_all('table'):
            soup_main = soup_table.find('div', attrs={'class': 'main'})
            if soup_main is not None and util.Util.trim_clean(soup_main.get_text()) == '出走レース':
                ret['races'] = self.parse_races(soup_table)
                break

        return ret
