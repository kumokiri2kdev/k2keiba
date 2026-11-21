""" Offline test helpers: run parsers against HTML saved by tools/capture_fixtures.py. """
import json
import os

import pytest

from k2kparser import (top, kaisai, den, odds, result, win5, uma, search,  # noqa: F401
                       tokubetsu, calendar)

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')

_MODULES = [top, kaisai, den, odds, result, win5, uma, search, tokubetsu, calendar]


def _find_class(name):
    for mod in _MODULES:
        if hasattr(mod, name):
            return getattr(mod, name)
    raise LookupError(name)


def parse_fixture(label, **attrs):
    """ Parse test/fixtures/<label>.html with the parser class recorded at capture time.
    Skips the test when the fixture has not been captured. """
    meta_path = os.path.join(FIXTURE_DIR, label + '.meta.json')
    if not os.path.exists(meta_path):
        pytest.skip('fixture not captured: {} (run tools/capture_fixtures.py)'.format(label))
    with open(meta_path, encoding='utf-8') as f:
        meta = json.load(f)
    ext = 'json.txt' if meta['class'] == 'ParserCalendar' else 'html'
    with open(os.path.join(FIXTURE_DIR, '{}.{}'.format(label, ext)), encoding='utf-8') as f:
        content = f.read()

    cls = _find_class(meta['class'])
    p = cls.__new__(cls)          # skip __init__: no URL / request needed
    p.uri = meta['uri']
    for k, v in attrs.items():
        setattr(p, k, v)
    return p.parse_html(content)


@pytest.fixture
def parse():
    return parse_fixture
