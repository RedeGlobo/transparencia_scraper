#!/usr/bin/env python
# coding: utf-8

# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license
# Copyright (c) 2017 Rede Globo


__author__ = "Priscilla Lusie"
__version__ = "1.2"

import os
import pandas as pd
import re
import requests
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .html_utils import Html_utils

class Diarias_Scraper(Html_utils):
    """
        Busca os dados presentes em http://www.portaltransparencia.gov.br/despesasdiarias/
        a partir da consulta por órgão superior, data inicial e data final.
        Gera uma tabela com os resultados disponibilizados pelo site de forma paginada.
        E salva o arquivo localmente.
    """
    def __init__(self, log=None, sleep_time=30):
    """
       Inicializa a classe com parâmetros importantes
       Args:
           log (object): instância do log a registrar mensagens de error, debug e warning
           sleep_time (int): tempo de sleep entre os requests feitos à página para não sobrecarregar o servidor
    """
        self.log = log
        self.url = 'http://www.portaltransparencia.gov.br/despesasdiarias/'
        self.sleep_time = sleep_time
        
    @staticmethod
    def load_time(date_in, date_out):
        """
            Seta a data inicial começando no dia 01 e 
            configura a data final terminando no dia 01 do mês seguinte ao mês desejado.
            Caso a data passada seja do mês corrente (Ex. estamos em 5/12 e a data final seja 20/12)
            a data final é alterada para o mês anterior pois se pegarmos os dados parciais,
            quando o mês finalizar os mesmos não serão capturados novamente.
            Args:
                date_in(str): data inicial de consulta no formato YYYY-mm-dd
                date_out(str): data final de consulta no formato YYYY-mm-dd
            Returns:
                Duas listas de datas iniciais e finais de mês em mês.
                Ex: 2016-01-01 a 2016-03-01 => gera date_in=[2016-01-01, 2016-02-01] e date_out=[2016-02-01, 2016-03-01]
        """
        current = time.strftime("%Y-%m-01")   
        if (not date_out) or (date_out > current):
            date_out = current
        if not date_in:
            last_month = datetime.now() - relativedelta(months=1)
            date_in = format(last_month, '%Y-%m-01')  
            
        # Crio um range de datas a ser consultado
        dates_in = pd.date_range(date_in, date_out, freq='1M')-pd.offsets.MonthBegin(1)
        dates_out = pd.date_range(date_in, date_out, freq='1M') 
        return dates_in, dates_out
    
    def get_org_sup(self, url):
        """ 
            Busca os órgaos disponíveis fazendo uma requisição em uma página de consulta com parâmetros quaisquer
            Args:
                url(str): página inicial com a combo de órgãos carregada
            Returns:
                a lista de órgãos disponíveis para consulta
        """
        soup = self.get_html(url)

        orgs = []
        res = soup.find_all('select', {'id': 'rapidaOS'})
        if not res or not len(res):
            if self.log:
                self.log.error('CAPTCHA')
            time.sleep(self.sleep_time)
            return None

        for t in res[0].find_all('option'):
            if t['value'] == 'TOD':
                continue
            orgs.append(t['value'])
        if self.log:
            self.log.debug('Encontrado {} órgãos: {}'.format(len(orgs), ', '.join(orgs)))
        return orgs[::-1]

    def check_downloaded_file(self, org, year, month, page):
        """  Recebe o nome do arquivo para que seja 
             conferido se o download do arquivo já foi feito ou não.
             Note:
                A classe deve ser derivada e o método sobrescrito.
             Args:
                org (str): nome do órgao superior consultado
                year (int): ano ao qual o dado se refere
                month(int): mês ao qual o dado se refere
                page (str): número da página processada em cada busca
             Returns:
                 True se o arquivo já foi processado anteriormente, caso contrário, False.
        """
        filename = '{}_{}{}_{}.csv'.format(org, year, str(month).zfill(2), page)
        from pathlib import Path
        if Path(filename).is_file():
            return True
        return False
    
    def get_page_content(self, soup, header):
        """
            Captura a tabela de resultados e seu cabeçalho em um conteúdo retornado por uma página web
            Args:
                soup: conteúdo retornado por uma página web
                header: Se for nulo, captura o header presente na tabela
            Returns:
                uma lista com os nomes das colunas da tabela
                uma lista com as linhas retornadas na tabela
        """
        # TABELA DE RESULTADOS
        contents = soup.find(class_='tabela')
        if not contents:
            if self.log:
                self.log.debug('Tabela vazia')
            return None, None

        if not header:
            header = [t.text.replace('\r', '').replace('\n', '').replace(' ', '').replace('&nbsp', '') for t in contents.find_all(class_='titulo_cabecalho')[0].find_all('th')]

        results = []
        result_rows = contents.find_all('tr')
        if not result_rows:
            if self.log:
                self.log.debug('vazio')
            return None, None
                
        return header, result_rows

    
    def process_rows(self, header, result_rows, org):
        """
            Converte a tabela retornada pela página ao se fazer uma busca por órgão e data
            em uma lista de dicionários com os dados rotulados de acordo com as informações do header da tabela.
            São incluídas 2 novas colunas: 
                * url - link para a página web com o detalhamento do documento retornado
                * cod_org_superior - número identificado na combo selecionada no momento de busca
            Args:
                header (list of strings): Lista com os nomes de cada coluna da tabela web
                result_rows (bs4.element.ResultSet): Linhas com os dados de diárias retornados pela página web
                org (int): código do órgão superior
            Returns:
                lista com os dados em formato de dicionário
        """
        results = []
        for index, t in enumerate(result_rows):
            if not index: # Pulo o header
                continue

            row = {}
            for h in zip(header, t.find_all('td')):
                text = h[1].text.replace('\n', '').replace('\r', '').strip()
                if h[0].lower().find('valor') != -1:
                    text = float(text.replace('(*)', '').strip())
                row[h[0]] = text
                if h[0] == 'Documento':
                    row['url'] = self.url + h[1].a['href']
                    row['cod_orgao_superior'] = org
            results.append(row)
        return results
    
    def save_results(self, org, year, month, page, header, results):
        """
            Cria um dataframe com os resultados e salva localmente em CSV.
            Returns:
                Nome do arquivo salvo; Caso o resultado da tabela seja vazio, retorna Nulo.
        """
        filename = '{}_{}{}_{}.csv'.format(org, year, str(month).zfill(2), page)
        df = pd.DataFrame(results, columns=header.extend(['url']))

        if df[header[0]].iloc[0].find('Nenhum documento obedece aos critérios da consulta') != -1:
            if self.log:
                self.log.debug('Nenhum documento obedece aos critérios da consulta')
            return None
        df.to_csv(filename, index=False)
        return filename
        
    def process(self, date_in=None, date_out=None):
        header = None

        dates_in, dates_out = self.load_time(date_in, date_out)

        orgs = self.get_org_sup(self.url + 'resultado?consulta=rapida&periodoInicio=14/11/2017&periodoFim=15/11/2017&&fase=PAG&codigoOS=63000&codigoFavorecido=')
        if not orgs:
            return False
                    
        # Realizo as consultas em si            
        for d in zip(dates_in, dates_out):
            if self.log:
                self.log.warning("############## Processando data {} ##############".format(d[0].strftime('%Y%m')))
            for index, org in enumerate(orgs):
                if self.log:
                    self.log.warning("%%%%%%%%%%% Processando orgao superior #{} - {} %%%%%%%%%%%".format(index, org))

                # fazendo a consulta para obter os dados                
                url = self.url + 'resultado?consulta=rapida&periodoInicio={}&periodoFim={}&&fase=PAG&codigoOS={}&codigoFavorecido='.format(d[0].strftime('%d/%m/%Y'), d[1].strftime('%d/%m/%Y'), org)
                if self.log:
                    self.log.debug(url)
                soup = self.get_html(url)

                # verificando a quantidade de páginas disponíveis
                num_pages = self.scrape_from_pattern(str(soup), '\<span class=\"paginaXdeN\"\>Página 1 de ([0-9]+)\<\/span\>')
                if num_pages:
                    num_pages = int(num_pages[0])
                else:
                    num_pages = 1
                    
                # iterando entre as páginas para carregar todos os resultados
                results = []
                for page in range(1, num_pages+1):
                    if self.check_downloaded_file(org, d[0].strftime('%Y'), d[0].strftime('%m'), page):
                        continue
                    url_page = url + '&pagina={}'.format(page)
                    if page != 1:
                        soup = self.get_html(url_page) 
                        
                    header, result_rows = self.get_page_content(soup, header)
                    time.sleep(self.sleep_time)
                    if not result_rows:
                        if page == num_pages: # última página
                            continue
                        else:
                            if self.log:
                                self.log.error('CAPTCHA')
                            return False
                    results = self.process_rows(header, result_rows, org)
                    if self.log:
                        self.log.debug('PAGE = {} de {} - {} itens'.format(page, num_pages, len(results)))
                    #results.extend(partial_results)

                    # salvando os resultados
                    self.save_results(org, d[0].strftime('%Y'), d[0].strftime('%m'), page, header, results)
            return True
                
