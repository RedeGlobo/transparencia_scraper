# coding: utf-8
#!/usr/bin/env python

__author__ = "Priscilla Lusie"
__version__ = "1.1"

import os
import re
import requests
import signal
import stat
import sys
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

def handler_ctrlz(signum, frame):
    print('Operacao interrompida pelo usuario')
    sys.exit(0)
signal.signal(signal.SIGTSTP, handler_ctrlz)

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
    
class File_utils:
    def __init__(self, log):
        self.log = log
        
    def download_file_from_url(self, url, params, filename):
        """
        Salva o arquivo no local desejado. 
        Printa o progresso de download do arquivo sendo cada '=' uma representação de 2% do arquivo salvo.
        Args:
            url (string): portal de download. Ex.: 'http://arquivos.portaldatransparencia.gov.br/downloads.asp'
            params (json): parametros a serem passados para a url. Devem ser passados:
                               ** ano desejado com 4 caracteres
                               ** mes desejado com 2 caracteres
                               ** base de dados a ser consultada. Ex: 'c: BolsaFamiliaFolhaPagamento'
            filename (string): nome do arquivo a ser salvo
        Exception:
            Lanca excecao em caso de algum erro
        """
        url = url.strip()

        # Checa a existencia da pasta de destino do arquivo
        folder = os.path.dirname(filename)
        if not os.path.exists(folder):
            os.makedirs(folder)
            os.chmod(folder, stat.S_IRWXU)

        # Requisicao para obter o tamanho do arquivo a ser baixado
        if self.log:
            self.log.debug('URL do arquivo a ser baixado: ' + url)
            
        r = requests.get(url, stream=True, params=params)
        if r is None:
            raise ValueError('Nenhuma resposta do site {} para o arquivo {}'.format(url, filename))

        total_length = r.headers.get('content-length')
        if total_length is None:
            total_length = 0
        total_length = int(total_length)
        load = 0
        if self.log:
            self.log.warning('Downloading {} [{}]:\n\turl {}\n\tparâmetros {}'.format(filename, 
                                                                                 self.get_readable_size(int(total_length)),
                                                                                 url,
                                                                                 params))

        # Download em si
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192*4):
                if not chunk:
                    log.debug('chunk nulo')
                    continue

                f.write(chunk)
                f.flush()
                os.fsync(f.fileno())

                # printa o status (tamanho) de download realizado
                load += len(chunk)
                self.check_progress(load, total_length)

                # Set the signal handler and a 5-second alarm
                signal.signal(signal.SIGALRM, self.handler)
                signal.alarm(300)

        # Desativa o alarme
        signal.alarm(0)
        print('\n')
        
    @staticmethod
    def get_readable_size(size, precision=2):
        """ 
            Exibe o tamanho do arquivo em Bytes e no formato Kilo, Mega, etc. 
            Args:
                size(int):
                precision(int): quantidade de dígitos de precisão depois da vírgula
            Returns:
                Tamanho do arquivo em float acompanhado dos sufixos B, KB, etc.
        """

        if not size or size == 0:
            return ''

        suffixes=['B','KB','MB','GB','TB']
        suffixIndex = 0
        while size > 1024 and suffixIndex < 4:
            suffixIndex += 1 
            size = size/1024.0 
        return "%.*f%s"%(precision,size,suffixes[suffixIndex])
    
    @staticmethod
    def check_progress(complete, total):
        """ Printa na tela o progresso de uma tarefa em uma escala de 1 a 50 sinais '='.
            Portanto, cada sinal '=' printado representa 2% da tarefa executada.
        Args:
            complete (double): representa o quanto foi feito
            total (double): valor total a ser feito
        """
        if not total or total == 0:
            return
        done = int(50 * complete / total)
        sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)) )
        sys.stdout.flush()
     
    @staticmethod
    def handler(signum, frame):
        raise IOError('Processo travado {}'.format(signum))


class Transparencia_Scraper(Html_utils, File_utils):
    """
        Classe para download dos arquivos relativos as bases disponibilizados pelo Governo Federal
        no site transparência.
    """
    def __init__(self, log=None):
        File_utils.__init__(self, log)
        self.url_main = 'http://portaldatransparencia.gov.br/downloads/'
        self.url_download = 'http://arquivos.portaldatransparencia.gov.br/downloads.asp'
            
    def __print_error_msg(self, msg):
        if self.log:
            self.log.error(msg)
        else:
            print(msg)
        
    def __get_links(self):
        links = []
        for item in self.scrape_from_tag('class', 'colunas', self.url_main):
            links.extend(item.find_all('a'))
        return links
    
    def __get_schema_info(self, url, link):
        """
            Separa a string que compoe a URL em componentes (parâmetros) importantes
            como o parâmentro c que identifica o nome da base.
            Algumas URLs não possuem o parâmetro c, sendo necessário fazer uma requisição
            ao link da base e buscar o parâmetro consulta no conteúdo retornado ao acessar sua URL.
            Args:
                url (str): endereço completo da base a ser consultada. 
                           Ex: http://portaldatransparencia.gov.br/downloads/mensal.asp?c=GastosDiretos
            Returns:
                * O nome da base
                * Os parâmetros presentes na URL
                * Caso o link da base seja uma URL para uma outra página, retorna o conteúdo desta; 
                  caso seja um link para ZIP, retorna NULO.
        """
        url_parsed = urlparse(url)
        params = parse_qs(url_parsed.query)
        content = None
        c = None
        
        if os.path.splitext(url)[1] != '.zip':
            content = requests.get(url).text

        if 'c' in params:
            c = params['c'][0]
        elif 'consulta' in params:
            c = params['consulta'][0]
        elif content: # base não informada na URL
            c = re.search('\'&consulta=(.*?)\'', content)
            if c is None or c.group(1) is None:
                return None, None, content
            c = c.group(1)
        return c, params, content
    
    def check_downloaded_file(self, filename, params):
        """  Recebe o nome da base, nome do arquivo e a partição da base para que seja 
             conferido se o download do arquivo já foi feito ou não.
             Note:
                A classe deve ser derivada e o método sobrescrito.
             Args:
                filename (str): nome do arquivo
                params (dict): parâmetros com informação do arquivo
             Returns:
                 True se o arquivo já foi processado anteriormente, caso contrário, False.
        """
        from pathlib import Path
        if Path(filename).is_file():
            return True
        return False
        
    def process_file(self, c, params, zip_filename, url_file):
        """
            Baixa o arquivo localmente para a pasta cujo nome é o mesmo da base ao qual o
            arquivo pertence
            Args:
                c (str): nome da base
                params (dict): Dicionário com os parâmetros necessários para a identificação do arquivo a ser baixado
                zip_filename (str): nome final que o arquivo a ser salvo deverá assumir
                url_file (str): endereço da url de download dos arquivos
            Returns:
                True caso o arquivo tenha sido baixado localmente e False caso contrário
        """
        if self.check_downloaded_file(zip_filename, params):
            return False
        self.download_file_from_url(url_file, params, zip_filename)
        return True
    
    def __get_file_info(self, c, file_param):
        original_c = c
        params = {'a': file_param[0], 'consulta': c}
        
        zip_filename = '{}'.format(params['a'])
        if file_param[1] != '_F': # month
            params['m'] = file_param[1]
            zip_filename += '_{}'.format(params['m'])
        if file_param[3] != '': # day
            params['d'] = file_param[3]
            zip_filename += '_{}'.format(params['d'])
        if file_param[5] != '': # type
            params['d'] = file_param[5]
            c += '_'+params['d']
        if file_param[7] != '': # origem
            params['o'] = file_param[7]
            c += '_'+params['o']
        zip_filename = '{}/{}.zip'.format(c, zip_filename)

        return params, zip_filename
        
    def process_schemas(self, process_copa=False):
        """
            A url inicial mostra as bases disponíveis para download.
            Cada base possui uma URL que é um link para uma página que possui os arquivos disponíveis e deve ser 'crawleada'
            Algumas bases são enviadas através do parâmetro c=NOME_DA_BASE, outras são enviadas como consulta=NOME_DA_BASE
            Exs de links: 
                * snapshot.asp?c=Convenios
                * mensal.asp?c=OutrasTransferenciasCidadao
                * imoveisFuncionais.asp
                * http://arquivos.portaldatransparencia.gov.br/downloads.asp?a=2015&amp;m=04&amp;consulta=Copa
            Args:
                process_copa (boolean): True caso se deseje que processe os arquivos da Copa. 
                    Default False uma vez que os dados não são atualizados e devem ser processados apenas uma única vez.
        """
        for l in self.__get_links():
            schema_url = (self.url_main + l['href'])

            schema_name, params, content = self.__get_schema_info(schema_url, l['href'])
            if not schema_name:
                self.__print_error_msg('Base não identificada na URL {}'.format(schema_url))
                continue
            if not process_copa and schema_name == 'Copa':
                continue
            
            if self.log:
                self.log.warning('###################################################')
                self.log.warning('Processando site {}'.format(schema_name))
            else:
                print('Processando site {}'.format(schema_name))
                

            if schema_name == 'Copa':
                self.process_file(schema_name, 
                                  params=None, 
                                  zip_filename=schema_name+'/'+schema_name+'.zip', 
                                  url_file=l['href'])

            else:
                scrap_pattern = r'{"ano":"([0-9]{4})","mes":"([0-9]{2}|_F)"(,"dia":"([0-9]*)")?(,"tipo":"?(\w*)")?(,"origem":"?(\w*)")?}'
                files_params = self.scrape_from_pattern(content, scrap_pattern)
                if self.log:
                    self.log.warning('Encontrados {} arquivos'.format(len(files_params)))

                for f in files_params:
                    params, zip_filename = self.__get_file_info(schema_name, f)
                    res = self.process_file(schema_name, params, zip_filename, self.url_download)
                
            folder = os.path.dirname(zip_filename)
            if os.path.exists(folder) and not os.listdir(folder):
                os.rmdir(folder)
