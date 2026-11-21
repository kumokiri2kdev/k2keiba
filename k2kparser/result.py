""" JRA Result (レース結果) Page Parsers

Output keys follow docs/naming.md.
"""
import logging
import re

from . import util
from . import parser
from . import den
from . import video
from .den import _onclick_link, _href_link, _race_num

logger = logging.getLogger(__name__)

# 払戻の券種（refund_unit の li の class 名と同じ）
PAYOUT_TYPES = ('win', 'place', 'wakuren', 'wide', 'umaren', 'umatan', 'trio', 'tierce')


class ParserResultTop(den.ParserDenTop):
    """ レース結果トップ（今週）: list of kaisai days. See ParserKaisaiTop.parse_content. """
    def __init__(self, path='/JRADB/accessS.html', param='pw01sli00/AF'):
        super().__init__(path, param)


class ParserResultKaisaiList(ParserResultTop):
    """ 過去のレース結果（月ごと）: list of kaisai days. See ParserKaisaiTop.parse_content. """
    def parse_days(self, soup):
        return soup.find_all('div', attrs={'class': 'past_result_line_unit'})


class ParserResultKaisai(parser.ParserPost):
    def parse_content(self, soup):
        """ 開催ごとのレース一覧
        :return: dict
            'date', 'weekday', 'kai', 'racecourse', 'nichi'
            'races': list of dict
                'race_num', 'name', 'condition', 'surface', 'distance', 'horse_count',
                'link': 結果, 'odds_link': オッズ
        """
        soup_table = soup.find('div', attrs={'id': 'contentsBody'}).find('table', attrs={'id': 'race_list'})
        ret = den.parse_kaisai_caption(soup_table)
        ret['races'] = []

        for soup_race in soup_table.find('tbody').find_all('tr'):
            race = {}
            soup_anchor = soup_race.find('th', attrs={'class': 'race_num'}).find('a')
            race['race_num'] = _race_num(soup_anchor.find('img'))

            soup_names = soup_race.find('td', attrs={'class': 'race_name'}).find('div').find_all('div')
            race['name'] = util.Util.trim_clean(soup_names[0].getText())
            condition = util.Util.trim_clean(soup_names[1].getText())
            race['condition'] = condition if condition != '' else race['name']

            race['surface'] = util.parse_surface(soup_race.find('td', attrs={'class': 'course'}).getText())
            race['distance'] = util.parse_int(soup_race.find('td', attrs={'class': 'dist'}).getText())
            horse_count = util.parse_int(soup_race.find('td', attrs={'class': 'num'}).getText())
            if horse_count is not None:
                race['horse_count'] = horse_count

            link = _href_link(soup_anchor)
            if link:
                race['link'] = link
            soup_odds = soup_race.find('td', attrs={'class': 'odds'})
            link = _onclick_link(soup_odds.find('a')) if soup_odds else None
            if link:
                race['odds_link'] = link

            ret['races'].append(race)

        return ret


class ParserResultRace(parser.ParserPost):
    def __init__(self, path, param, fetch_video=False, **kwargs):
        """
        :param fetch_video: True なら、レース映像・全周パトロールの HLS の URL も取得する
                            （映像1本につき CDN へ2回アクセスする）
        """
        self.fetch_video = fetch_video
        super().__init__(path, param, **kwargs)

    def parse(self):
        race = super().parse()
        if getattr(self, 'fetch_video', False) and race.get('videos'):
            video.resolve_videos(race['videos'])
        return race

    def parse_payouts(self, soup_li):
        """ One bet type of the refund area -> list of dict(combination, payout, popularity) """
        payouts = []
        if soup_li is None:
            return payouts
        for soup_line in soup_li.find_all('div', attrs={'class': 'line'}):
            combination = util.Util.trim_clean(soup_line.find('div', attrs={'class': 'num'}).getText())
            if combination == '':
                continue
            payout = {'combination': combination,
                      'payout': util.parse_int(soup_line.find('div', attrs={'class': 'yen'}).getText())}
            popularity = util.parse_int(soup_line.find('div', attrs={'class': 'pop'}).getText())
            if popularity is not None:
                payout['popularity'] = popularity
            payouts.append(payout)
        return payouts

    def parse_horse(self, soup_tr):
        horse = {}

        position = util.Util.trim_clean(soup_tr.find('td', attrs={'class': 'place'}).getText())
        try:
            horse['finish_position'] = int(position)
        except ValueError:
            horse['finish_position'] = None
            horse['finish_status'] = position

        horse['waku'] = util.parse_int(soup_tr.find('td', attrs={'class': 'waku'}).find('img')['alt'])
        horse['horse_num'] = util.parse_int(soup_tr.find('td', attrs={'class': 'num'}).getText())

        soup_name = soup_tr.find('td', attrs={'class': 'horse'})
        horse['name'] = util.Util.trim_clean(soup_name.getText())
        link = _href_link(soup_name.find('a'))
        if link:
            horse['link'] = link

        parsed = util.Util.parse_age(soup_tr.find('td', attrs={'class': 'age'}).getText())
        horse['age'] = parsed[0]
        horse['sex'] = parsed[1]

        hande = util.parse_float(soup_tr.find('td', attrs={'class': 'weight'}).getText())
        if hande is not None:
            horse['hande'] = hande

        soup_jockey = soup_tr.find('td', attrs={'class': 'jockey'})
        horse['jockey'] = util.person(util.Util.trim_clean(soup_jockey.getText()), _onclick_link(soup_jockey.find('a')))

        finish_time = util.Util.trim_clean(soup_tr.find('td', attrs={'class': 'time'}).getText())
        if finish_time != '':
            try:
                horse['finish_time'] = util.Util.parse_race_time(finish_time)
            except util.UtilError:
                logger.info('finish time parse error: {}'.format(finish_time))

        margin = util.Util.trim_clean(soup_tr.find('td', attrs={'class': 'margin'}).getText())
        if margin != '':
            horse['margin'] = margin

        soup_corner = soup_tr.find('div', attrs={'class': 'corner_list'})
        if soup_corner is not None:
            corner_positions = {}
            for soup_li in soup_corner.find_all('li'):
                position = util.parse_int(soup_li.getText())
                if position is not None and soup_li.has_attr('title'):
                    corner_positions[re.sub(r'[^0-9]', '', soup_li['title'])] = position
            if corner_positions:
                horse['corner_positions'] = corner_positions

        last_3f = util.Util.trim_clean(soup_tr.find('td', attrs={'class': 'f_time'}).getText())
        if last_3f != '':
            try:
                horse['last_3f'] = util.Util.parse_race_time(last_3f)
            except util.UtilError:
                logger.debug('last 3F parse error: {}'.format(last_3f))

        body_weight = soup_tr.find('td', attrs={'class': 'h_weight'}).getText().strip()
        if body_weight != '':
            try:
                horse['body_weight'], horse['body_weight_diff'] = util.Util.parse_weight(body_weight)
            except ValueError:
                logger.warning('Body weight parse error: {}'.format(body_weight))

        soup_trainer = soup_tr.find('td', attrs={'class': 'trainer'})
        horse['trainer'] = util.person(util.Util.trim_clean(soup_trainer.getText()),
                                       _onclick_link(soup_trainer.find('a')))

        popularity = util.parse_int(soup_tr.find('td', attrs={'class': 'pop'}).getText())
        if popularity is not None:
            horse['popularity'] = popularity

        return horse

    def parse_content(self, soup):
        """ レース結果（1レース）
        :return: dict
            'date', 'weekday', 'kai', 'racecourse', 'nichi', 'race_num', 'departure',
            'name', 'grade', 'category', 'class', 'rule', 'weight_rule', 'distance', 'surface', 'course',
            'weather': 天候, 'track_condition': 馬場状態,
            'den_link': 出馬表, 'odds_link': オッズ,
            'horses': list of dict
                'finish_position', 'finish_status', 'waku', 'horse_num', 'name', 'link', 'age', 'sex',
                'hande', 'jockey', 'finish_time', 'margin', 'corner_positions', 'last_3f',
                'body_weight', 'body_weight_diff', 'trainer', 'popularity'
            'laps': list of int (0.1秒)
            'last_furlongs': {'3F': int, '4F': int}
            'corner_orders': {'1': str, ...}
            'payouts': {券種: list of dict(combination, payout, popularity)}
            'videos': {'race': レース映像, 'patrol': 全周パトロール}（ボタンがある場合）
                'video_id'
                'master_url', 'resolutions', 'duration'（fetch_video=True のとき）
        """
        soup_result = soup.find('div', attrs={'id': 'contentsBody'}).find('div', attrs={'class': 'race_result_unit'})
        race = den.parse_race_header(soup_result)

        soup_weather = soup_result.find('li', attrs={'class': 'weather'})
        if soup_weather is not None:
            race['weather'] = util.Util.trim_clean(soup_weather.find('span', attrs={'class': 'txt'}).getText())
        soup_track = soup_result.find('li', attrs={'class': 'turf'}) or soup_result.find('li', attrs={'class': 'durt'})
        if soup_track is not None:
            race['track_condition'] = util.Util.trim_clean(soup_track.find('span', attrs={'class': 'txt'}).getText())
        else:
            logger.info('Track condition not found')

        soup_links = soup_result.find('div', attrs={'class': 'race_related_link'})
        if soup_links is not None:
            for soup_anchor in soup_links.find_all('a'):
                if soup_anchor.has_attr('onclick') and 'accessO' in soup_anchor['onclick']:
                    link = _onclick_link(soup_anchor)
                    if link:
                        race['odds_link'] = link
                elif soup_anchor.has_attr('href') and 'accessD' in soup_anchor['href']:
                    link = _href_link(soup_anchor)
                    if link:
                        race['den_link'] = link

        race['horses'] = [self.parse_horse(soup_tr) for soup_tr in soup_result.find('tbody').find_all('tr')]

        soup_result_time = soup_result.find('div', attrs={'class': 'result_time_data'})
        if soup_result_time is not None:
            soup_tds = soup_result_time.find_all('td')

            laps = []
            for lap in soup_tds[0].getText().split('-'):
                try:
                    laps.append(util.Util.parse_race_time(lap))
                except util.UtilError:
                    logger.debug('Parse Time Error: {}'.format(lap))
            race['laps'] = laps

            if len(soup_tds) > 1:
                last_furlongs = {}
                for value in soup_tds[1].getText().split('-'):
                    values = util.Util.trim_clean(value).split(' ')
                    try:
                        last_furlongs[values[0]] = util.Util.parse_race_time(values[-1])
                    except util.UtilError:
                        logger.debug('Parse Time Error: {}'.format(value))
                race['last_furlongs'] = last_furlongs

        soup_result_corner = soup_result.find('div', attrs={'class': 'result_corner_place'})
        if soup_result_corner is not None:
            corner_orders = {}
            for soup_tr in soup_result_corner.find_all('tr'):
                corner_orders[re.sub(r'[^0-9]', '', soup_tr.find('th').getText())] = \
                    util.Util.trim_clean(soup_tr.find('td').getText())
            race['corner_orders'] = corner_orders

        soup_refund = soup_result.find('div', attrs={'class': 'refund_area'})
        if soup_refund is not None:
            soup_refund = soup_refund.find('div', attrs={'class': 'refund_unit'})
            payouts = {}
            for payout_type in PAYOUT_TYPES:
                lines = self.parse_payouts(soup_refund.find('li', attrs={'class': payout_type}))
                if lines:
                    payouts[payout_type] = lines
            race['payouts'] = payouts

        # 開催中は、映像のボタンが遅れて追加されることがある（ない場合はキーを省略）
        videos = video.parse_video_ids(soup_result)
        if videos:
            race['videos'] = videos

        return race
