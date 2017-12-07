# coding: utf-8
#!/usr/bin/env python

__author__ = "Priscilla Lusie"
__version__ = "1.0"

import re
import requests
from bs4 import BeautifulSoup

class Html_utils:
    @staticmethod
    def get_html(url, decode_content=False):
        """ 
            Converte o resultado retornado pela URL em um estrutura html 
            Args:
                url (str): endereço completo da página a ser consultada
                decode_content (boolean): True caso seja desejável a conversão para utf-8; Default False.
            Returns:
                Conteúdo retornado pela página em estrutura html usando BeautifulSoup
        """
        r = requests.get(url)
        if decode_content:
            text = str(r.content, 'utf-8', errors='replace')
        else:
            text = r.content
        return BeautifulSoup(text, 'lxml')

    def scrape_from_tag(self, tag_name, tag_value, url, root_tag='div'):
        soup = self.get_html(url)
        content = soup.findAll(root_tag, attrs={tag_name: tag_value})
        return content

    def scrape_from_pattern(self, html, pattern, url=None):
        if url:
            html = str(self.get_html(url))
        files = re.findall(pattern, html, re.MULTILINE)
        return files
