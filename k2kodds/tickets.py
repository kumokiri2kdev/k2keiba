""" Bet types, expanding a bet (formation / box / combinations) into tickets, and which tickets a finish hits. """
from itertools import combinations, permutations, product

# bet type -> (number of horses, order matters)
BET_TYPES = {
    'win': (1, True),           # 単勝
    'wakuren': (2, False),      # 枠連 (bracket numbers)
    'umaren': (2, False),       # 馬連
    'wide': (2, False),         # ワイド (any 2 of the first 3)
    'umatan': (2, True),        # 馬単
    'trio': (3, False),         # 3連複
    'tierce': (3, True),        # 3連単
}


class OddsError(ValueError):
    """ Invalid bet or odds (the message is for the user). """


def key_of(bet_type, numbers):
    """ (2, 1) -> '1-2' for unordered bet types, as in k2kparser's odds dicts """
    size, ordered = BET_TYPES[bet_type]
    return '-'.join(str(n) for n in (numbers if ordered else sorted(numbers)))


def expand(bet):
    """ One bet -> list of ticket keys (no duplicates, in a stable order).

    bet: {'bet_type': ..., and one of
          'formation': [[1st...], [2nd...], [3rd...]]   (one list per position; for unordered types the
                                                       positions are just groups, e.g. 軸 and 相手)
          'box': [horses]
          'combinations': ['1-2-3', ...]
          'horses': [horses]                         (same as box; natural for win)}
    """
    bet_type = bet.get('bet_type')
    if bet_type not in BET_TYPES:
        raise OddsError('Unknown bet_type: {!r}. Use one of: {}'.format(bet_type, ', '.join(BET_TYPES)))
    size, ordered = BET_TYPES[bet_type]
    same_allowed = bet_type == 'wakuren'        # 枠連 1-1 (two horses in bracket 1)

    if bet.get('combinations'):
        numbers_list = []
        for text in bet['combinations']:
            try:
                numbers = tuple(int(n) for n in str(text).split('-'))
            except ValueError:
                raise OddsError('Invalid combination: {!r}'.format(text))
            if len(numbers) != size:
                raise OddsError('{} needs {} numbers: {!r}'.format(bet_type, size, text))
            numbers_list.append(numbers)
    elif bet.get('formation'):
        groups = bet['formation']
        if len(groups) != size or not all(groups):
            raise OddsError('{} formation needs {} non-empty groups, got {!r}'.format(bet_type, size, groups))
        numbers_list = list(product(*groups))
    elif bet.get('box') or bet.get('horses'):
        horses = list(dict.fromkeys(bet.get('box') or bet.get('horses')))
        if len(horses) < size:
            raise OddsError('{} box needs at least {} horses: {!r}'.format(bet_type, size, horses))
        numbers_list = list(permutations(horses, size) if ordered else combinations(horses, size))
    else:
        raise OddsError('A bet needs formation, box, horses or combinations: {!r}'.format(bet))

    keys = []
    for numbers in numbers_list:
        if not same_allowed and len(set(numbers)) != len(numbers):
            continue
        keys.append(key_of(bet_type, numbers))
    keys = list(dict.fromkeys(keys))
    if not keys:
        raise OddsError('The {} bet has no valid combination: {!r}'.format(bet_type, bet))
    return keys


def hit_keys(order, waku_of=None):
    """ Finish (1st, 2nd, 3rd) -> {bet_type: [ticket keys that win]} """
    a, b, c = order
    hits = {
        'win': [str(a)],
        'umaren': [key_of('umaren', (a, b))],
        'wide': [key_of('wide', pair) for pair in ((a, b), (a, c), (b, c))],
        'umatan': [key_of('umatan', (a, b))],
        'trio': [key_of('trio', order)],
        'tierce': [key_of('tierce', order)],
    }
    if waku_of and a in waku_of and b in waku_of:
        hits['wakuren'] = [key_of('wakuren', (waku_of[a], waku_of[b]))]
    return hits
