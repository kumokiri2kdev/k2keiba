""" JRA Page Top Parser """

from . import parser
from . import util

class ParserTop(parser.Parser):
    def __init__(self):
        super(ParserTop, self).__init__('/')

    def parse_content(self, soup):
        """ Parse content and return parameters if exist
        :param soup:
        :return: Dict of parameters(URL and Post parameter)
            'kaisai': 開催情報
            'shutuba': 出馬表
            'odds': オッズ
            'haraimodoshi': レース結果
            'tokubetu': 特別レース登録馬

        """
        param_list = {}
        qmenu = soup.find('div', attrs={'id': 'quick_menu'})

        if qmenu is None:
            raise parser.ParseError

        content = qmenu.find('div', attrs={"class": "content"})
        if content is None:
            raise parser.ParseError

        links = content.find_all('li')
        for link in links:
            anchor = link.find('a')
            if anchor.has_attr('onclick'):
                try :
                    params = util.Util.parse_func_params(anchor['onclick'])
                    if params[0].endswith('accessI.html'):
                        # 開催情報
                        param_list['kaisai'] = util.Util.format_params(params)
                    elif params[0].endswith('accessD.html'):
                        # 出馬表
                        param_list['shutuba'] = util.Util.format_params(params)
                    elif params[0].endswith('accessO.html'):
                        # オッズ
                        param_list['odds'] = util.Util.format_params(params)
                    elif params[0].endswith('accessH.html'):
                        # print("払い戻し : {}".format(params[1]))
                        param_list['haraimodoshi'] = util.Util.format_params(params)
                    elif params[0].endswith('accessS.html'):
                        # print("レース結果 : {}".format(params[1]))
                        param_list['race'] = util.Util.format_params(params)
                    elif params[0].endswith('accessT.html'):
                        # print("特別レース登録馬 : {}".format(params[1]))
                        param_list['tokubetu'] = util.Util.format_params(params)
                except parser.ParseError as per:
                    pass

        return param_list
