""" Capture JRA pages as local fixtures.

Walks the JRA site once (top -> kaisai/den/odds/result/win5/uma/search/tokubetsu/calendar),
and for every page saves:
    test/fixtures/<label>.html       : decoded page body (UTF-8)
    test/fixtures/<label>.meta.json  : parser class, URL, POST parameter
    test/fixtures/<label>.json       : parser output at capture time

Usage:
    python tools/capture_fixtures.py [--delay SEC]
"""
import argparse
import json
import logging
import os
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from k2kparser import parser as pr          # noqa: E402
from k2kparser import top, kaisai, den, odds, result, win5, uma, search, tokubetsu, calendar  # noqa: E402
from k2kparser import result_params         # noqa: E402

FIXTURE_DIR = os.path.join(ROOT, 'test', 'fixtures')
logger = logging.getLogger('capture')

_captured = []
_delay = 2.0


def _record(orig):
    def wrapper(self, content):
        _captured.append({'class': type(self).__name__, 'uri': self.uri,
                          'param': self.data.decode('utf-8') if self.method == 'POST' else None,
                          'content': content})
        return orig(self, content)
    return wrapper


def _throttle(orig):
    def wrapper(self):
        time.sleep(_delay)
        return orig(self)
    return wrapper


pr.Parser.parse_html = _record(pr.Parser.parse_html)
pr.ParserJson.parse_html = _record(pr.ParserJson.parse_html)
pr.Parser.parse = _throttle(pr.Parser.parse)


def save(label, output, page=-1):
    """ Save the page captured at index `page` (default: the latest) under `label`. """
    page = _captured[page]
    ext = 'json.txt' if page['class'] == 'ParserCalendar' else 'html'
    with open(os.path.join(FIXTURE_DIR, '{}.{}'.format(label, ext)), 'w', encoding='utf-8') as f:
        f.write(page['content'])
    meta = {k: page[k] for k in ('class', 'uri', 'param')}
    with open(os.path.join(FIXTURE_DIR, label + '.meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    with open(os.path.join(FIXTURE_DIR, label + '.json'), 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    logger.info('saved %s (%s)', label, page['class'])
    return output


def step(label, fn):
    try:
        return fn()
    except BaseException as e:  # ParseError derives from BaseException
        if isinstance(e, KeyboardInterrupt):
            raise
        logger.error('FAILED %s: %r', label, e)
        traceback.print_exc()
        return None


def link_of(d, *keys):
    for k in keys:
        try:
            d = d[k]
        except (KeyError, IndexError, TypeError):
            return None
    return d


def main():
    global _delay
    ap = argparse.ArgumentParser()
    ap.add_argument('--delay', type=float, default=2.0)
    ap.add_argument('--result-month', type=int, default=202510, help='YYYYMM for past result list')
    args = ap.parse_args()
    _delay = args.delay
    os.makedirs(FIXTURE_DIR, exist_ok=True)

    step('top', lambda: save('top', top.ParserTop().parse()))
    step('kaisai', lambda: save('kaisai', kaisai.ParserKaisai().parse()))

    # --- Den (出馬表) ---
    den_top = step('den_top', lambda: save('den_top', den.ParserDenTop().parse()))
    den_kaisai = None
    if den_top:
        day = den_top[0]['kaisai'][0]
        den_kaisai = step('den_kaisai', lambda: save(
            'den_kaisai', den.ParserDenKaisai(day['link']['url'], day['link']['param']).parse()))
    den_race = None
    if den_kaisai:
        # Prefer the main race (11R) if present
        races = den_kaisai['races']
        race = next((r for r in races if r['race_num'] == 11), races[-1])
        den_race = step('den_race', lambda: save(
            'den_race', den.ParserDenRace(race['link']['url'], race['link']['param']).parse()))

    # --- Uma (馬) ---
    horse_link = link_of(den_race, 'horses', 0, 'link') if den_race and den_race.get('horses') else None
    if horse_link:
        step('uma', lambda: save('uma', uma.ParserUma(horse_link['url'], horse_link['param']).parse()))

    # --- WIN5 ---
    win5_link = next((d['win5_link'] for d in (den_top or []) if 'win5_link' in d), None)
    if win5_link:
        w = step('win5', lambda: save('win5', win5.ParserWin5Kaisai(win5_link['url'], win5_link['param']).parse()))
        prev = link_of(w, 'prev_link')
        if prev:
            step('win5_past', lambda: save('win5_past', win5.ParserWin5Kaisai(prev['url'], prev['param']).parse()))

    # --- Odds ---
    odds_top = step('odds_top', lambda: save('odds_top', odds.ParserOddsTop().parse()))
    odds_kaisai = None
    if odds_top:
        day = odds_top[0]['kaisai'][0]
        odds_kaisai = step('odds_kaisai', lambda: save(
            'odds_kaisai', odds.ParserOddsKaisai(day['link']['url'], day['link']['param']).parse()))
    if odds_kaisai:
        races = odds_kaisai['races']
        race = next((r for r in races if r['race_num'] == 11), races[-1])
        odds_classes = [
            ('win', odds.OddsParserWin), ('wakuren', odds.OddsParserBracketQuinella),
            ('umaren', odds.OddsParserBracket), ('wide', odds.OddsParserWide),
            ('umatan', odds.OddsParserExacta), ('trio', odds.OddsParserTrio),
            ('tierce', odds.OddsParserTierce),
        ]
        for tag, cls in odds_classes:
            link = race['odds_links'].get(tag)
            if link:
                label = 'odds_tanpuku' if tag == 'win' else 'odds_' + tag
                step(label, lambda: save(label, cls(link['url'], link['param']).parse()))

    # --- Result (今週) ---
    result_top = step('result_top', lambda: save('result_top', result.ParserResultTop().parse()))
    result_kaisai = None
    if result_top:
        day = result_top[0]['kaisai'][0]
        result_kaisai = step('result_kaisai', lambda: save(
            'result_kaisai', result.ParserResultKaisai(day['link']['url'], day['link']['param']).parse()))
    if result_kaisai:
        race = next((r for r in result_kaisai['races'] if r['race_num'] == 11), result_kaisai['races'][-1])
        step('result_race', lambda: save(
            'result_race', result.ParserResultRace(race['link']['url'], race['link']['param']).parse()))

    # --- Result (過去) ---
    cname = result_params.ParserRaceParams.get_cname(args.result_month)
    step('result_kaisai_list', lambda: save(
        'result_kaisai_list', result.ParserResultKaisaiList('/JRADB/accessS.html', cname).parse()))

    # --- Search ---
    step('search', lambda: save('search', search.ParserSearch('/JRADB/accessR.html', 'pw02uliD1', 'アイアン').parse()))

    # --- Tokubetsu (特別レース登録馬) ---
    top_links = json.load(open(os.path.join(FIXTURE_DIR, 'top.json'), encoding='utf-8')) \
        if os.path.exists(os.path.join(FIXTURE_DIR, 'top.json')) else []
    toku_link = next((t['link'] for t in top_links if t['tag'] == 'tokubetsu'), None)
    if toku_link:
        toku = step('tokubetsu_top', lambda: save(
            'tokubetsu_top', tokubetsu.ParserTokubetuTop(toku_link['url'], toku_link['param']).parse()))
        race_link = link_of(toku, 0, 'kaisai', 0, 'races', 0, 'link')
        if race_link:
            step('tokubetsu_race', lambda: save(
                'tokubetsu_race', tokubetsu.ParserTokubetuRace(race_link['url'], race_link['param']).parse()))

    # --- Calendar (fetches the month JSON and every race day page of the month) ---
    def calendar_step():
        start = len(_captured)
        out = calendar.ParserCalendar().parse()
        save('calendar', out, page=start)               # JSON page
        if len(_captured) > start + 1 and out:
            save('calendar_month', out[0]['races'], page=start + 1)  # first race-day page
        return out
    step('calendar', calendar_step)

    logger.info('done: %d pages fetched', len(_captured))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
    main()
