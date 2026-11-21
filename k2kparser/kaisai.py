""" JRA Kaisai (今週の開催情報) Page Parser

Output keys follow docs/naming.md.
"""
import logging

from . import util
from . import parser

logger = logging.getLogger(__name__)


class ParserKaisai(parser.ParserPost):

    def __init__(self, path='/JRADB/accessI.html', param='pw01ide01/4F', **kwargs):
        super().__init__(path, param, **kwargs)

    def parse_racecourses(self, soup_unit):
        soup_block = soup_unit.find('div', attrs={'class': 'weather_block'})
        if soup_block is None:
            return []

        # Columns are aligned by position. Some columns are empty (no meeting at that slot).
        names = [util.Util.trim_clean(th.get_text())
                 for th in soup_block.find('thead').find_all('th', attrs={'class': 'rc'})]
        racecourses = [{'racecourse': name} if name else None for name in names]

        soup_tbody = soup_block.find('tbody')

        soup_weather = soup_tbody.find('tr', attrs={'class': 'weather'})
        if soup_weather is not None:
            for i, soup_td in enumerate(soup_weather.find_all('td', recursive=False)):
                text = util.Util.trim_clean(soup_td.get_text())
                if i < len(racecourses) and racecourses[i] is not None and text:
                    racecourses[i]['weather'] = text

        soup_baba = soup_tbody.find('tr', attrs={'class': 'baba'})
        if soup_baba is not None:
            for i, soup_td in enumerate(soup_baba.find_all('td', recursive=False)):
                if i >= len(racecourses) or racecourses[i] is None:
                    continue
                track_condition = {}
                for soup_cap in soup_td.find_all('span', attrs={'class': 'cap'}):
                    soup_main = soup_cap.parent.find('span', attrs={'class': 'main'})
                    if soup_main is None:
                        continue
                    if 'turf' in soup_cap['class']:
                        track_condition['turf'] = util.Util.trim_clean(soup_main.get_text())
                    elif 'dirt' in soup_cap['class']:
                        track_condition['dirt'] = util.Util.trim_clean(soup_main.get_text())
                if track_condition:
                    racecourses[i]['track_condition'] = track_condition

        return [rc for rc in racecourses if rc is not None]

    def parse_content(self, soup):
        """ 今週の開催情報（天候・馬場状態）
        :return: dict
            'date', 'weekday'
            'racecourses': list of dict
                'racecourse': 競馬場
                'weather': 天候
                'track_condition': {'turf': 芝, 'dirt': ダート}
        """
        ret = {}
        soup_unit = soup.find('div', attrs={'class': 'kaisai_info_unit'})
        if soup_unit is None:
            return ret

        header = soup_unit.find('div', attrs={'class': 'contents_header'}).find('div', attrs={'class': 'main'})
        header = header.get_text()
        ret['date'] = util.to_iso_date(header)
        weekday = util.parse_weekday(header)
        if weekday:
            ret['weekday'] = weekday

        ret['racecourses'] = self.parse_racecourses(soup_unit)

        return ret
