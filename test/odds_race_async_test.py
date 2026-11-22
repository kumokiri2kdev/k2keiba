""" Fetch every odds page (7 bet types) of a race at once with coroutines (aparse).

The race is given by the CNAME of one of its odds pages (any bet type). That page is fetched first and the
other bet types are fetched in parallel from its 'odds_links'. Odds are published only for this week.

    cd test
    python odds_race_async_test.py [CNAME ...]
"""
import asyncio
import logging
import logging.config
import sys
import time
sys.path.insert(0, '../')

from k2kparser import aio, odds as po

# 5th character of the CNAME ('pw151ou...') -> (bet type, parser)
PARSERS = {
    '1': ('win', po.OddsParserWin),                     # 単勝・複勝
    '3': ('wakuren', po.OddsParserBracketQuinella),     # 枠連
    '4': ('umaren', po.OddsParserBracket),              # 馬連
    '5': ('wide', po.OddsParserWide),                   # ワイド
    '6': ('umatan', po.OddsParserExacta),               # 馬単
    '7': ('trio', po.OddsParserTrio),                   # 3連複
    '8': ('tierce', po.OddsParserTierce),               # 3連単
}
PARSER_OF = dict(PARSERS.values())

logger = logging.getLogger(__name__)


def summary(bet_type, data):
    """ number of entries and the 3 lowest odds """
    if bet_type == 'win':
        top = sorted((h for h in data if h['win'] is not None), key=lambda h: h['win'])[:3]
        return '{:4} 頭    {}'.format(len(data), ', '.join('{}番 {}'.format(h['horse_num'], h['win']) for h in top))
    values = {k: (v['min'] if isinstance(v, dict) else v) for k, v in data.items()}
    top = sorted((kv for kv in values.items() if kv[1] is not None), key=lambda kv: kv[1])[:3]
    return '{:4} 通り  {}'.format(len(data), ', '.join('{} {}'.format(k, v) for k, v in top))


async def fetch_race(cname):
    bet_type, parser_class = PARSERS[cname[4]]
    start = time.perf_counter()
    async with aio.AsyncClient() as client:
        first = await parser_class('/JRADB/accessO.html', cname).aparse(client)
        links = {t: link for t, link in first['odds_links'].items() if t != bet_type and t in PARSER_OF}
        pages = await asyncio.gather(*(PARSER_OF[t](link['url'], link['param']).aparse(client)
                                       for t, link in links.items()))
    elapsed = time.perf_counter() - start

    results = {bet_type: first, **dict(zip(links, pages))}
    for t in PARSER_OF:
        if t in results:
            logger.info('  {:8} {}'.format(t, summary(t, results[t]['odds'])))
    logger.info('  {} ページ {:.2f} 秒'.format(len(results), elapsed))
    return results


if __name__ == '__main__':
    logging.config.fileConfig('logging.ini', disable_existing_loggers=False)

    races = [
        'pw151ouS308202605051120261121Z/C8',     # 2026年11月21日 京都11R シトリンステークス
        'pw151ouS303202603051120261121Z/F4',     # 2026年11月21日 福島11R 福島記念
        'pw151ouS308202605061120261122Z/F8',     # 2026年11月22日 京都11R マイルチャンピオンシップ
    ]

    # python odds_race_async_test.py [CNAME ...]  (CNAME of any odds page of the race)
    if len(sys.argv) > 1:
        races = sys.argv[1:]

    for race in races:
        logger.info(race)
        asyncio.run(fetch_race(race))
