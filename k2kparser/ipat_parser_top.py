
from . import ipat_parser as ipat


class IPatParserTop(ipat.IPatParser):
    def __init__(self, **kwargs):
        super(ipat.IPatParser, self).__init__('/', **kwargs)

    def parse_content(self, soup):
        print(soup)


if __name__ == '__main__':
    p = IPatParserTop()


    p.parse()



