""" JRA Page Top Parser

Output keys follow docs/naming.md.
"""
import logging

from . import util
from . import parser


logger = logging.getLogger(__name__)

# リンク先 -> tag
TAG_TABLE = {
    'accessI.html': 'kaisai',       # 開催情報
    'accessD.html': 'den',          # 出馬表
    'accessO.html': 'odds',         # オッズ
    'accessH.html': 'payout',       # 払戻金
    'accessS.html': 'result',       # レース結果
    'accessT.html': 'tokubetsu',    # 特別レース登録馬
    'accessR.html': 'search',       # 競走馬検索
}

SEARCH_LINK = {'url': '/JRADB/accessR.html', 'param': 'pw02uliD1'}


class ParserTop(parser.Parser):
    def __init__(self, **kwargs):
        super(ParserTop, self).__init__('/', **kwargs)

    def parse_content(self, soup):
        """ トップページのクイックメニュー
        :return: list of dict
            'tag': 'kaisai' | 'den' | 'odds' | 'payout' | 'result' | 'tokubetsu' | 'search'
            'link': link
        """
        qmenu = soup.find('div', attrs={'id': 'quick_menu'})
        if qmenu is None:
            logger.error('ParseError : "quick menu" not found')
            raise parser.ParseError

        content = qmenu.find('div', attrs={'class': 'inner'})
        if content is None:
            raise parser.ParseError

        ret = []
        for soup_li in content.find_all('li'):
            soup_anchor = soup_li.find('a')
            if soup_anchor is None or not soup_anchor.has_attr('onclick'):
                continue
            try:
                link = util.Util.parse_func_params(soup_anchor['onclick'])
            except parser.ParseError:
                logger.debug('Anchor parse error: ' + soup_anchor.getText())
                continue

            tag = next((t for page, t in TAG_TABLE.items() if link['url'].endswith(page)), None)
            if tag is None:
                logger.warning('Unknown URL: ' + link['url'])
                continue
            ret.append({'tag': tag, 'link': link})

        # 競走馬検索がメニューにない場合は、既知のリンクを足す
        if ret and not any(item['tag'] == 'search' for item in ret):
            ret.append({'tag': 'search', 'link': dict(SEARCH_LINK)})

        return ret
