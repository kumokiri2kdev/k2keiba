""" JRA Result Page Parser """
import logging
import re

from . import util
from . import parser

logger = logging.getLogger(__name__)


class ParserResultTop(parser.ParserPost):

    def parse_days(self, soup):
        soup_area = soup.find('div', attrs = {'id':'contentsBody'})
        soup_day_area = soup_area.find('div', attrs = {'id':'main'})
        soup_days = soup_day_area.find_all('div', attrs = {'class':'panel'})

        return soup_days


    def parse_content(self, soup):
        """ Parse content and return parameters if exist
        :param soup:
        :return: Array of Dict of Kaisai
            'date': 日付
            'kaisai': Array of Kaisai information
                'index': 開催回数
                'day': 開催日（何日目）
                'place': 競馬場
                'params': URL and Post parameter

        """
        # soup_area = soup.find('div', attrs = {'id':'contentsBody'})
        # soup_day_area = soup_area.find('div', attrs = {'id':'main'})
        # soup_days = soup_day_area.find_all('div', attrs = {'class':'panel'})
        soup_days = self.parse_days(soup)
        kaisai_list = []
        for soup_day in soup_days:
            kaisai_info = {}
            header = util.Util.trim_clean(soup_day.find('h3').getText())

            kaisai_info['date'] = header.replace(' ','')
            kaisai_info['kaisai'] = []

            soup_links = soup_day.find('ul', attrs={'class': 'link_list'})
            soup_kaisai_list = soup_links.find_all('li')
            for soup_kaisai in soup_kaisai_list:
                kaisai_info_day = {}
                soup_anchor = soup_kaisai.find('a')
                if soup_anchor is None: # ToDo
                    break

                if soup_anchor.has_attr('onclick'):
                    try:
                        params = util.Util.parse_func_params(soup_anchor['onclick'])
                    except parser.ParseError as per:
                        logger.info('Anchor parse error: ' + soup_anchor.getText())

                try:
                    kaisai_param = util.Util.parse_kaisai(soup_kaisai.getText())
                except ValueError:
                    logger.info('parse_kaisai error: ' + soup_kaisai.getText())

                kaisai_info_day['index'] = kaisai_param[0]
                kaisai_info_day['day'] = kaisai_param[1]
                kaisai_info_day['place'] = kaisai_param[2]
                kaisai_info_day['param'] = util.Util.format_params(params)

                kaisai_info['kaisai'].append(kaisai_info_day)

            kaisai_list.append(kaisai_info)

            soup_win5 = soup_day.find('ul', attrs={'class': 'win5'})
            if soup_win5 is not None:
                soup_anchor = soup_win5.find('a')
                if soup_anchor is not None:
                    if soup_anchor.has_attr('onclick'):
                        try:
                            params = util.Util.parse_func_params(soup_anchor['onclick'])
                            kaisai_info['win5'] = params
                        except parser.ParseError as per:
                            logger.info('Anchor parse error: ' + soup_anchor.getText())


        return kaisai_list


class ParserResultKaisaiList(ParserResultTop):

    def parse_days(self, soup):
        soup_days = soup.find_all('div', attrs={'class': 'past_result_line_unit'})

        return soup_days

class ParserResultKaisai(parser.ParserPost):

    def parse_content(self, soup):
        kaisai_list = {}

        soup_area = soup.find('div', attrs={'id': 'contentsBody'})
        soup_table = soup_area.find('table', attrs={'id': 'race_list'})
        soup_caption = soup_table.find('caption')
        soup_caption_main = soup_caption.find('div', attrs={'class': 'main'})
        date, weekday, index, place, nichisuu = util.Util.parse_kaisai_date(soup_caption_main.getText())
        kaisai_list['date'] = date
        kaisai_list['weekday'] = weekday
        kaisai_list['index'] = index
        kaisai_list['place'] = place
        kaisai_list['nichisuu'] = nichisuu
        kaisai_list['races'] = []

        soup_tbody = soup_table.find('tbody')
        soup_races = soup_tbody.find_all('tr')
        for soup_race in soup_races:
            race = {}
            soup_anchor = soup_race.find('a')
            if soup_anchor.has_attr('onclick'):
                try:
                    params = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

            soup_img = soup_anchor.find('img')
            race_index = int(soup_img['alt'].replace('レース', ''))

            race['index'] = race_index
            race['param'] = util.Util.format_params(params)

            soup_course = soup_race.find('td', attrs={'class': 'course'})
            race['course'] = soup_course.getText()

            soup_race_name = soup_race.find('td', attrs={'class': 'race_name'}).find_all('li')
            race_name = util.Util.trim_clean(soup_race_name[0].getText())
            race_cond = util.Util.trim_clean(soup_race_name[1].getText())
            if race_cond == '':
                race_cond = race_name
            race['name'] = race_name
            race['cond'] = race_cond

            soup_num = soup_race.find('td', attrs={'class': 'num'})
            race['uma_num'] = int(soup_num.getText().replace('頭',''))

            soup_dist = soup_race.find('td', attrs={'class': 'dist'})
            dist = int(soup_dist.getText().replace('メートル', '').replace(',', ''))
            race['dist'] = dist

            kaisai_list['races'].append(race)

        return kaisai_list



class ParserResultRace(parser.ParserPost):

    def parse_pay_off(self, soup):
        pay_off = []

        soup_lines = soup.find_all('span', attrs={'class': 'line'})
        for soup_line in soup_lines:
            pay_off_unit = {}
            pay_off_unit['tag'] = util.Util.trim_clean(soup_line.find('span', attrs={'class': 'num'}).getText())
            if pay_off_unit['tag'] == '':
                return []
            pay_off_unit['price'] = \
                int(soup_line.find('span', attrs={'class': 'yen'}).getText().replace('円','').replace(',',''))
            pay_off_unit['fav'] = int(soup_line.find('span', attrs={'class': 'pop'}).getText().replace('番人気',''))
            pay_off.append(pay_off_unit)

        return pay_off


    def parse_content(self, soup):
        race = {}

        soup_area = soup.find('div', attrs={'id': 'contentsBody'})
        soup_result = soup_area.find('div',  attrs={'class': 'race_result_unit'})

        soup_date = soup_result.find('div', attrs={'class': 'date'})
        date, weekday, index, place, nichisuu = util.Util.parse_kaisai_date(soup_date.getText())

        race['date'] = date
        race['weekday'] = weekday
        race['index'] = index
        race['place'] = place
        race['nichisuu'] = nichisuu

        soup_weather = soup_result.find('li', attrs={'class': 'weather'})
        race['weather'] = util.Util.trim_clean(soup_weather.find('span', attrs={'class': 'txt'}).getText())

        soup_track_cond = soup_result.find('li', attrs={'class': 'turf'})
        if soup_track_cond is None:
            soup_track_cond = soup_result.find('li', attrs={'class': 'durt'})
            if soup_track_cond is None: # Still not found
                logging.error('Track Condition')

        race['course'] = util.Util.trim_clean(soup_track_cond.find('span', attrs={'class': 'cap'}).getText())
        race['course_cond'] = util.Util.trim_clean(soup_track_cond.find('span', attrs={'class': 'txt'}).getText())

        race['departure'] = soup_result.find('div', attrs={'class': 'time'}).find('strong').getText()

        race['index'] = int(soup_result.find('div', attrs={'class': 'race_number'}).
                            find('img')['alt'].replace('レース', ''))

        soup_name = soup_result.find('span', attrs={'class': 'race_name'})
        race['name'] = util.Util.trim_clean(soup_name.getText())

        soup_grade = soup_name.find('span', attrs={'class': 'grade_icon'})
        if soup_grade is None:
            logger.debug('None Grade Race')
        else:
            race['grade'] = soup_grade.find('img')['alt']

        soup_type = soup_result.find('div', attrs={'class': 'type'})
        race['category'] = soup_type.find('div', attrs={'class': 'category'}).getText()
        race['class'] = soup_type.find('div', attrs={'class': 'class'}).getText()
        race['rule'] = soup_type.find('div', attrs={'class': 'rule'}).getText()
        race['weight'] = soup_type.find('div', attrs={'class': 'weight'}).getText()
        distance, course = \
            util.Util.parse_course_distance(soup_type.find('div', attrs={'class': 'course'}).getText())
        race['distance'] = distance
        race['course'] = course

        soup_links = soup_result.find('div', attrs={'class': 'race_related_link'})

        soup_odds_link = soup_links.find('li')
        if soup_odds_link is not None:
            soup_anchor = soup_odds_link.find('a')
            if soup_anchor.has_attr('onclick'):
                try:
                    race['odds'] = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

        soup_tbody = soup_result.find('tbody')

        race['horses'] = []
        soup_trs = soup_tbody.find_all('tr')
        for i, soup_tr in enumerate(soup_trs):
            horse = {}
            soup_place = soup_tr.find('td', attrs={'class': 'place'})
            try :
                horse['place'] = int(soup_place.getText())
            except ValueError:
                horse['place'] = soup_place.getText()

            soup_waku = soup_tr.find('td', attrs={'class': 'waku'}).find('img')
            horse['waku'] = util.Util.parse_int_only(soup_waku['alt'])

            soup_waku = soup_tr.find('td', attrs={'class': 'num'})
            horse['num'] = util.Util.parse_int_only(soup_waku.getText())

            soup_name = soup_tr.find('td', attrs={'class': 'horse'})
            horse['name'] = util.Util.trim_clean(soup_name.getText())
            soup_anchor = soup_name.find('a')
            if soup_anchor is not None and soup_anchor.has_attr('onclick'):
                try:
                    horse['url'] = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

            age, sex = util.Util.parse_age(soup_tr.find('td', attrs={'class': 'age'}).getText())
            horse['age'] = age
            horse['sex'] = sex

            horse['hande'] = float(util.Util.trim_clean(
                soup_tr.find('td', attrs={'class': 'weight'}).getText()).replace('kg',''))

            soup_jockey = soup_tr.find('td', attrs={'class': 'jockey'})
            jockey = {}
            jockey['name'] = util.Util.trim_clean(soup_jockey.getText())
            soup_anchor = soup_jockey.find('a')
            if soup_anchor is not None and soup_anchor.has_attr('onclick'):
                try:
                    jockey['url'] = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())
                    horse['jockey'] = jockey

            try :
                finish = util.Util.trim_clean(soup_tr.find('td', attrs={'class': 'time'}).getText())
                horse['finish'] = util.Util.parse_race_time(finish)
            except util.UtilError:
                if finish == '':
                    logger.debug('Finish Time is None: {}'.format(finish))
                else:
                    logger.info('finish parse error: {}'.format(finish))

            margin = util.Util.trim_clean(soup_tr.find('td', attrs={'class': 'margin'}).getText())
            if margin != '':
                horse['margin'] = margin

            soup_corner = soup_tr.find('div', attrs={'class': 'corner_list'})
            if soup_corner is not None:
                soup_lis = soup_corner.find_all('li')
                horse['corner'] = {}
                for soup_li in soup_lis:
                    li = util.Util.trim_clean(soup_li.getText())
                    if li == '':
                        logger.debug('Corner info is missing')
                    else:
                        try :
                            horse['corner'][re.sub(r'[^0-9]', '', soup_li['title'])] = \
                                util.Util.parse_int_only(soup_li.getText())
                        except util.UtilError:
                            logger.info('Corner info is missing or malformed:', soup_li.getText())

            try :
                horse['flap'] = util.Util.parse_race_time(soup_tr.find('td', attrs={'class': 'f_time'}).getText())
            except util.UtilError:
                logger.debug('F Time parse error')
            except:
                logger.info('F Time parse error')

            try:
                soup_weight = soup_tr.find('td', attrs={'class': 'h_weight'})
                horse['weight'], horse['weight_diff'] = util.Util.parse_weight(soup_weight.getText())

            except:
                logger.warning('Weight parse error')

            soup_trainer = soup_tr.find('td', attrs={'class': 'trainer'})
            trainer = {}
            trainer['name'] = util.Util.trim_clean(soup_trainer.getText())
            soup_anchor = soup_trainer.find('a')
            if soup_anchor is not None and soup_anchor.has_attr('onclick'):
                try:
                    trainer['url'] = util.Util.parse_func_params(soup_anchor['onclick'])
                except parser.ParseError as per:
                    logger.info('Anchor parse error: ' + soup_anchor.getText())

            horse['trainer'] = trainer

            try :
                horse['win_fav'] = int(soup_tr.find('td', attrs={'class': 'pop'}).getText())
            except ValueError:
                if soup_tr.find('td', attrs={'class': 'pop'}).getText() == '':
                    logger.info('win_fav parse empty')
                else:
                    logger.error('win_fav parse fail')

            race['horses'].append(horse)


        soup_result_time = soup_result.find('div', attrs={'class': 'result_time_data'})
        if soup_result_time is not None:
            soup_tds = soup_result_time.find_all('td')

            laps = soup_tds[0].getText().split('-')
            for i, lap in enumerate(laps):
                try :
                    laps[i] = util.Util.parse_race_time(lap)
                except util.UtilError:
                    logger.debug('Parse Time Error: {}'.format(lap))
                    laps.remove(lap)
                except:
                    logger.info('Parse Time Error: {}'.format(lap))

            race['laps'] = laps

            ftime = {}
            if len(soup_tds) > 1:
                ftimes = soup_tds[1].getText().split('-')
                for ftime_val in ftimes:
                    ftime_vals = util.Util.trim_clean(ftime_val).split(' ')
                    ftime[ftime_vals[0]] = util.Util.parse_race_time(ftime_vals[-1])

            race['ftime'] = ftime


        soup_result_corner = soup_result.find('div', attrs={'class': 'result_corner_place'})
        if soup_result_corner is not None:
            soup_trs = soup_result_corner.find_all('tr')
            corner = {}
            for soup_tr in soup_trs:
                soup_th = soup_tr.find('th')
                soup_td = soup_tr.find('td')
                corner[re.sub(r'[^0-9]', '', soup_th.getText())] = util.Util.trim_clean(soup_td.getText())
            race['corner'] = corner
        else :
            logger.info('No Corner Info')

        soup_result_payoff = soup_result.find('div', attrs={'class': 'refund_area'})
        soup_result_payoff = soup_result_payoff.find('div', attrs={'class', 'refund_unit'})
        pay_off = {}
        pay_off_types = ('win', 'place', 'wakuren', 'wide', 'umaren', 'umatan', 'trio', 'tierce')
        for pay_off_type in pay_off_types:
            soup_pay_off_type = soup_result_payoff.find('li', attrs={'class': pay_off_type})
            pay_off[pay_off_type] = self.parse_pay_off(soup_pay_off_type)
            if len(pay_off[pay_off_type]) < 1:
                del pay_off[pay_off_type]

        race['pay_off'] = pay_off

        return race



