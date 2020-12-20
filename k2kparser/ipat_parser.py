from . import parser


IPAT_BASE_URL = 'https://www.ipat.jra.go.jp/'


class IPatParser(parser.Parser):
    @property
    def base_url(self):
        return IPAT_BASE_URL

    @property
    def decoder(self):
        return "'euc-jp'"


if __name__ == '__main__':
    pass
