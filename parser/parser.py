""" Parser Base Class """
import os

from bs4 import BeautifulSoup
import urllib.request

JRA_BASE_URL = 'http://www.jra.go.jp'


class ParseError(Exception):
	def __init__(self):
		pass

class Parser:
    def __init__(self, file_path, **kwargs):
        self.uri = self.gen_asb_uri(file_path)

        if 'data' in kwargs:
            self.method = 'POST'
            self.data = kwargs['data'].encode('utf-8')
        else:
            self.method = 'GET'

    def gen_asb_uri(self, file_path):
        return JRA_BASE_URL + file_path

    def parse_html(self, content):
        soup = BeautifulSoup(content, "html.parser")
        return self.parse_content(soup)

    def parse(self):
        if self.method == 'POST':
            request = urllib.request.Request(self.uri, data=self.data, method='POST')
        else:
            request = urllib.request.Request(self.uri)

        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("'Shift_JISx0213'")

        return self.parse_html(response_body)

    def parse_content(self, soup):
        print("Base Class parse_content must not  be called")


