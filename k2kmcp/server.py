""" MCP server exposing k2keiba (JRA horse racing data) as tools.

Run:  k2keiba-mcp             (stdio transport, for Claude Code / Claude Desktop)
      k2keiba-mcp --http      (Streamable HTTP at http://127.0.0.1:8000/mcp, for remote clients such as ChatGPT)
"""
import argparse
from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field

import k2kodds
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from k2kparser import parser
from .navigator import Navigator, NotFound, horse_id_of

INSTRUCTIONS = """\
Tools for JRA (Japan Racing Association) horse racing data, fetched live from www.jra.go.jp.

- Dates are 'YYYY-MM-DD'. Racecourses are Japanese names (東京, 中山, 京都, 阪神, 中京, 新潟, 福島, 小倉, 札幌, 函館);
  romanized names (Tokyo, Kyoto, ...) are also accepted.
- Race cards (出馬表) are published only for this week's meetings. Call list_meetings first to see them.
- Odds: current odds this week; for past races the final odds (確定オッズ) through the result page.
- Race results are available for this week and for past dates (since 1986).
- Times are in units of 0.1 second (693 = 1:09.3). Money is in yen.
- Each call fetches pages from JRA; avoid calling the same tool repeatedly for the same data.

Comparing ways of buying (馬券の買い方の比較):
- When the user gives marks (本命 / 対抗 / 連下, or A, B, C ...) and a budget, or asks which bet type or which
  horses to keep, use compare_bets. Do not compute odds, probabilities or payouts by hand.
- Put the user's plan and its variations (drop one horse at a time, another bet type, allocation='payout')
  in one call, up to 10 strategies with short unique names. Use horse numbers (馬番); check them with
  get_race_card, or get_race_result for past races.
- Report per strategy: points, hit probability, return when hit (min / median / max), torigami probability.
  Use 'finishes' to explain what a variation gives up (e.g. the payout lost if a dropped horse comes in).
- The probabilities are the market's view read from the odds, not a prediction; say so. For past races the
  final odds are used, so the comparison shows how the choices looked before the race.
"""

DateArg = Annotated[str, Field(description="Race date, 'YYYY-MM-DD'")]
RacecourseArg = Annotated[str, Field(description="Racecourse, e.g. '東京', '京都' (or 'Tokyo', 'Kyoto')")]
RaceNumArg = Annotated[int, Field(ge=1, le=12, description='Race number (1-12)')]

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True)

server = MCPServer('k2keiba', instructions=INSTRUCTIONS)
navigator = Navigator()


# ---- output shaping ----

def _clean(value):
    """ Drop page links (url/param) that only the parsers need; keep horse ids. """
    if isinstance(value, list):
        return [_clean(v) for v in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for key, item in value.items():
        if key == 'link' or key.endswith('_link') or key.endswith('_links') or key == 'contract_company_no':
            continue
        out[key] = _clean(item)
    horse_id = horse_id_of(value.get('link')) if isinstance(value.get('link'), dict) else None
    if horse_id:
        out = {'horse_id': horse_id, **out}
    return out


async def _call(coro):
    try:
        return await coro
    except NotFound as e:
        raise ToolError(str(e))
    except parser.ParseErrorHTTP as e:
        raise ToolError('JRA returned HTTP {}. Try again later.'.format(e.code))
    except parser.ParseError:
        raise ToolError('Could not fetch or read the JRA page (network error or page layout change).')


# ---- meetings / races ----

@server.tool(annotations=READ_ONLY)
async def list_meetings() -> dict[str, Any]:
    """List this week's JRA race meetings (開催) whose race cards are published.

    Returns each day with its meetings (racecourse, kai = 開催回, nichi = 開催日次) and whether WIN5 is held.
    Use the date and racecourse with the other tools.
    """
    days = await _call(navigator.den_days())
    return {'days': [{
        'date': day['date'],
        'weekday': day.get('weekday'),
        'meetings': [{k: m[k] for k in ('racecourse', 'kai', 'nichi') if k in m} for m in day['kaisai']],
        'win5': 'win5_link' in day,
    } for day in days]}


@server.tool(annotations=READ_ONLY)
async def get_track_conditions() -> dict[str, Any]:
    """Current weather and track condition (馬場状態: 良/稍重/重/不良) of this week's racecourses."""
    return _clean(await _call(navigator.track_conditions()))


@server.tool(annotations=READ_ONLY)
async def list_races(date: DateArg, racecourse: RacecourseArg) -> dict[str, Any]:
    """List the races (1R-12R) of a meeting: race number, name, condition, surface (芝/ダート/障害), distance (m),
    number of runners and post time. Works for this week (from the race cards) and past dates (from the results).
    """
    try:
        races = await navigator.race_list(date, racecourse, 'den')
        races['source'] = 'race_card'
    except NotFound:
        races = await _call(navigator.race_list(date, racecourse, 'result'))
        races['source'] = 'result'
    except parser.ParseError:
        races = await _call(navigator.race_list(date, racecourse, 'result'))
        races['source'] = 'result'
    return _clean(races)


@server.tool(annotations=READ_ONLY)
async def get_race_card(date: DateArg, racecourse: RacecourseArg, race_num: RaceNumArg) -> dict[str, Any]:
    """Race card (出馬表) of a race this week: race conditions and every runner with waku (枠番), horse_num (馬番),
    horse_id, sex/age, hande (斤量, kg), jockey, trainer, pedigree (sire/dam/broodmare_sire), body weight
    and current win odds / popularity (単勝人気) when published.
    Use get_horse with horse_id for a horse's past races.
    """
    return _clean(await _call(navigator.race_card(date, racecourse, race_num)))


# ---- odds ----

def _combination_odds(odds, bet_type, horse_nums, limit):
    rows = []
    for combination, value in odds.items():
        numbers = [int(n) for n in combination.split('-')]
        if horse_nums and not set(horse_nums) <= set(numbers):
            continue
        if bet_type == 'wide':
            row = {'combination': combination, 'min': value and value.get('min'), 'max': value and value.get('max')}
            sort_value = row['min']
        else:
            row = {'combination': combination, 'odds': value}
            sort_value = value
        rows.append((sort_value is None, sort_value or 0, row))
    rows.sort(key=lambda r: (r[0], r[1]))
    return len(rows), [r[2] for r in rows[:limit]]


@server.tool(annotations=READ_ONLY)
async def get_odds(
        date: DateArg,
        racecourse: RacecourseArg,
        race_num: RaceNumArg,
        bet_type: Annotated[
            Literal['win', 'wakuren', 'umaren', 'wide', 'umatan', 'trio', 'tierce'],
            Field(description="win = 単勝・複勝, wakuren = 枠連, umaren = 馬連, wide = ワイド, umatan = 馬単, "
                              "trio = 3連複, tierce = 3連単")] = 'win',
        horse_nums: Annotated[Optional[list[int]], Field(
            description='Only combinations that include all of these horse numbers (枠番 for wakuren)')] = None,
        limit: Annotated[int, Field(ge=1, le=500, description='Max combinations to return, lowest odds first')] = 30,
) -> dict[str, Any]:
    """Odds of a race: current odds this week, final odds (確定オッズ) for past races.

    win: win odds (単勝) and place odds range (複勝 min/max) of every horse.
    Other bet types: combinations sorted by odds (most popular first), limited to `limit`; use horse_nums to
    narrow down (e.g. [5] for every combination with horse 5). Odds of None mean cancelled / no votes.
    """
    page = await _call(navigator.odds(date, racecourse, race_num, bet_type))
    out = {'bet_type': bet_type}
    if 'updated_at' in page:
        out['updated_at'] = page['updated_at']
    if bet_type == 'win':
        horses = page['odds']
        if horse_nums:
            horses = [h for h in horses if h.get('horse_num') in horse_nums]
        out['odds'] = horses
    else:
        total, rows = _combination_odds(page['odds'], bet_type, horse_nums, limit)
        out.update({'matched_combinations': total, 'returned': len(rows), 'odds': rows})
    if 'votes' in page:
        out['votes'] = page['votes']
    return out


# ---- comparing ways of buying (k2kodds) ----

BetTypeArg = Literal['win', 'wakuren', 'umaren', 'wide', 'umatan', 'trio', 'tierce']


class Bet(BaseModel):
    """ One bet: give exactly one of formation, box or combinations. """
    bet_type: BetTypeArg = Field(description='win = 単勝, wakuren = 枠連 (bracket numbers), umaren = 馬連, '
                                             'wide = ワイド, umatan = 馬単, trio = 3連複, tierce = 3連単')
    formation: Optional[list[list[int]]] = Field(None, description=(
        'One list of horse numbers per position: [[1st], [2nd], [3rd]] for tierce/umatan. For trio/umaren/wide '
        'the lists are groups, e.g. 軸1頭流し A-BC-BCDEF = [[A], [B, C], [B, C, D, E, F]]. win: [[A, B]]'))
    box: Optional[list[int]] = Field(None, description='Box (ボックス): every combination of these horses')
    combinations: Optional[list[str]] = Field(None, description="Explicit tickets, e.g. ['1-2-3', '1-2-5']")
    amount: Optional[int] = Field(None, description='Fixed yen per ticket (multiple of 100); '
                                                    'otherwise the budget is allocated')


class Strategy(BaseModel):
    name: str = Field(description="Short unique name, e.g. 'trio A-BC-BCDEF' or 'drop D'")
    bets: list[Bet] = Field(description='Bets bought together (can mix bet types)')
    allocation: Optional[Literal['equal', 'payout']] = Field(None, description='Overrides the allocation')


@server.tool(annotations=READ_ONLY)
async def compare_bets(
        date: DateArg,
        racecourse: RacecourseArg,
        race_num: RaceNumArg,
        strategies: Annotated[list[Strategy], Field(min_length=1, max_length=10, description=(
            'Ways of buying to compare, e.g. a base plan and variations (drop a horse, umaren instead of trio)'))],
        budget: Annotated[int, Field(ge=100, le=1000000, description='Yen per strategy')] = 3000,
        allocation: Annotated[Literal['equal', 'payout'], Field(description=(
            'equal = same amount per ticket; payout = more on low odds so that every hit pays about the same'
        ))] = 'equal',
        wide_odds: Annotated[Literal['min', 'max', 'mid'], Field(
            description='Wide odds are a range; which end to use')] = 'min',
        table_size: Annotated[int, Field(ge=0, le=100, description='Max rows of the finish table')] = 20,
) -> dict[str, Any]:
    """Compare ways of buying tickets for a race by hit probability and return, using the current odds this week
    or the final odds of a past race (to review how other ways of buying would have compared).

    For each strategy: points, tickets with amounts, hit_probability, profit_probability (payout > spent),
    torigami_probability (hit but payout < spent), payout_when_hit / return_when_hit (min/median/max, return =
    payout / spent) and market_return_rate (expected payout / spent under the market's probabilities; usually
    about 0.7-0.8 because of the takeout). 'finishes' lists likely finishes with the payout of every strategy,
    e.g. what is lost by dropping a horse. 'horses' gives each used horse's chance to win / be top 2 / top 3.

    Probabilities are the market's view read from the tierce (3連単) odds, not a prediction. Odds change until the
    race starts, so payouts are estimates for races not run yet. Use the horse numbers from get_race_card.
    """
    used = {bet.bet_type for s in strategies for bet in s.bets}
    needed = sorted(used | {'tierce'} | ({'win'} if 'wakuren' in used else set()))
    pages = await _call(navigator.odds_of_types(date, racecourse, race_num, needed))
    odds = {t: page['odds'] for t, page in pages.items()}
    try:
        result = k2kodds.compare([s.model_dump(exclude_none=True) for s in strategies], odds, budget=budget,
                                 allocation=allocation, wide=wide_odds, table_size=table_size)
    except k2kodds.OddsError as e:
        raise ToolError(str(e))
    updated = [page['updated_at'] for page in pages.values() if page.get('updated_at')]
    if updated:
        result['odds_updated_at'] = max(updated)
    return result


# ---- results ----

@server.tool(annotations=READ_ONLY)
async def get_race_result(
        date: DateArg,
        racecourse: RacecourseArg,
        race_num: RaceNumArg,
        include_video: Annotated[bool, Field(
            description='Also get HLS URLs of the race replay and the patrol video (slower). The URLs are for '
                        'playback only: the videos are copyrighted, so do not help download, save or '
                        'redistribute them')] = False,
) -> dict[str, Any]:
    """Result of a race (this week or past, since 1986): finishing order with times (0.1 s units), margins,
    corner positions, last 3F, popularity, body weight, lap times and payouts (払戻) of every bet type.
    """
    return _clean(await _call(navigator.race_result(date, racecourse, race_num, fetch_video=include_video)))


# ---- horses ----

@server.tool(annotations=READ_ONLY)
async def search_horses(
        name: Annotated[str, Field(description='Horse name in katakana (2+ characters); prefix match')],
        status: Annotated[Literal['all', 'active', 'inactive'], Field(
            description='active = 現役, inactive = 抹消 (retired)')] = 'all',
) -> dict[str, Any]:
    """Search JRA horses by name. Returns horse_id, name, sex, age, trainer and whether the horse is active."""
    horses = _clean(await _call(navigator.search_horses(name, status)))
    return {'count': len(horses), 'horses': horses}


@server.tool(annotations=READ_ONLY)
async def get_horse(
        horse_id: Annotated[str, Field(description='10-digit horse_id from get_race_card / search_horses')],
        max_races: Annotated[int, Field(ge=0, le=200, description='Max past races to return (newest first)')] = 20,
) -> dict[str, Any]:
    """Profile (pedigree, birthday, owner, trainer, breeder) and past races of a horse
    (date, racecourse, race, distance, track condition, popularity, finishing position, jockey, time, winner).
    """
    horse = _clean(await _call(navigator.horse(horse_id)))
    races = horse.get('races', [])
    horse['races'] = races[:max_races]
    horse['total_races'] = sum(1 for r in races if r.get('type') == 'race')
    return horse


def _inline_refs(schema):
    """ Replace {'$ref': '#/$defs/Name'} with the definition itself and drop '$defs'.
    Some MCP clients do not resolve $ref and leave such tools out. """
    defs = schema.get('$defs', {})

    def resolve(node):
        if isinstance(node, list):
            return [resolve(n) for n in node]
        if not isinstance(node, dict):
            return node
        if '$ref' in node:
            name = node['$ref'].rsplit('/', 1)[-1]
            merged = {**defs[name], **{k: v for k, v in node.items() if k != '$ref'}}
            return resolve(merged)
        return {k: resolve(v) for k, v in node.items() if k != '$defs'}

    return resolve(schema)


for _tool in server._tool_manager.list_tools():     # SDK internals: the schema served by tools/list
    _tool.parameters = _inline_refs(_tool.parameters)


LOCAL_HOSTS = ('127.0.0.1', 'localhost', '::1')


def transport_security(host, allow_hosts):
    """ Host/Origin checks of the HTTP transport (protection against DNS rebinding).

    Bound to localhost, the SDK accepts only localhost Host headers. Behind a tunnel or a reverse proxy the
    Host header is the public name, so it has to be added with allow_hosts. Returns None for the SDK default.
    """
    if not allow_hosts:
        return None
    hosts, origins = [], []
    if host in LOCAL_HOSTS:
        hosts += ['127.0.0.1:*', 'localhost:*', '[::1]:*']
        origins += ['http://127.0.0.1:*', 'http://localhost:*', 'http://[::1]:*']
    for name in allow_hosts:
        hosts.append(name)
        origins.append('https://' + name)
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts,
                                     allowed_origins=origins)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='k2keiba-mcp', description='MCP server of k2keiba (JRA horse racing data)')
    ap.add_argument('--http', action='store_true',
                    help='serve Streamable HTTP at http://HOST:PORT/mcp instead of stdio')
    ap.add_argument('--host', default='127.0.0.1', help='address to bind with --http (default: 127.0.0.1)')
    ap.add_argument('--port', type=int, default=8000, help='port with --http (default: 8000)')
    ap.add_argument('--allow-host', action='append', default=[], metavar='NAME',
                    help='also accept this Host header, e.g. the tunnel name xxxx.trycloudflare.com (repeatable)')
    args = ap.parse_args(argv)

    if not args.http:
        if args.allow_host:
            ap.error('--allow-host needs --http')
        server.run('stdio')
        return
    server.run('streamable-http', host=args.host, port=args.port,
               transport_security=transport_security(args.host, args.allow_host))


if __name__ == '__main__':
    main()
