""" JRA Page Top Parser """
import logging

from . import util
from . import parser


logger = logging.getLogger(__name__)

class ParserTop(parser.Parser):
    def __init__(self, **kwargs):
        super(ParserTop, self).__init__('/', **kwargs)

    def parse_content(self, soup):
        """ Parse content and return parameters if exist
        :param soup:
        :return: Array of dict of parameters(URL and Post parameter)
            'tag': タグ
                'kaisai': 開催情報, 'shutuba': 出馬表, 'odds': オッズ, 'haraimodoshi': レース結果,'tokubetu': 特別レース登録馬
            'params': Dict of URL and Post parameter
                'url':  URL,
                'param': Prameter
        """
        param_list = {}
        qmenu = soup.find('div', attrs={'id': 'quick_menu'})

        if qmenu is None:
            logger.error('ParseError : "quick menu" not found')
            raise parser.ParseError

        content = qmenu.find('div', attrs={"class": "inner"})
        if content is None:
            raise parser.ParseError

        links = content.find_all('li')

        param_list = []

        for link in links:
            anchor = link.find('a')
            if anchor.has_attr('onclick'):
                tag = ''
                try :
                    params = util.Util.parse_func_params(anchor['onclick'])
                    if params['url'].endswith('accessI.html'):
                        # 開催情報
                        tag = 'kaisai'
                    elif params['url'].endswith('accessD.html'):
                        # 出馬表
                        tag = 'shutuba'
                    elif params['url'].endswith('accessO.html'):
                        # オッズ
                        tag = 'odds'
                    elif params['url'].endswith('accessH.html'):
                        # 払い戻し
                        tag = 'haraimodoshi'
                    elif params['url'].endswith('accessS.html'):
                        # レース結果
                        tag = 'result'
                    elif params['url'].endswith('accessT.html'):
                        # 特別レース登録馬
                        tag = 'tokubetu'
                    else:
                        logger.warning('Unknown URL: ' + params['url'])
                        continue
                except parser.ParseError:
                    logger.debug('Anchor parse error: ' + anchor.getText())
                    continue

                param_list.append({
                    'tag': tag,
                    'link': params
                })

        if len(param_list) > 0:
            param_list.append({
                'tag': 'search',
                'link': {
                    'url': '/JRADB/accessR.html',
                    'param': 'pw02uliD1'
                }
            })

        return param_list
