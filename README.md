# transparencia_scraper
Projeto para captura de dados disponíveis pelo governo federal no portal de transparência: www.portaltransparencia.gov.br.

Alguns arquivos são disponibilizados diariamente e outros mensalmente em formato CSV.

Os dados são divididos em bases (pastas) como CPGF, BolsaFamiliaFolhaPagamento, BolsaFamiliaSacado, etc.

# Arquivos
  * html_utils.py => classe com métodos para apoio ao processamento de páginas web
  * transparencia_scraper.py => classe para obtenção dos arquivos presentes em http://arquivos.portaldatransparencia.gov.br/downloads.asp
  * diarias_scraper.py => classe para obtenção dos dados presentes nas consultas realizadas em http://www.portaltransparencia.gov.br/despesasdiarias/

# Exemplo:

Segue um exemplo de como usar a classe Transparencia_Scraper:

```
import logging 
log = logging.getLogger(__name__)
scrap = Transparencia_Scraper(log)
scrap.process_schemas(process_copa=False)
```

Segue um exemplo de como usar a classe Diarias_Scraper:

```
import logging
log = logging.getLogger(__name__)
scrap = Diarias_Scraper(log)
scrap.process()
```

Caso seja desejável filtrar um período específico:

```
import logging
log = logging.getLogger(__name__)
scrap = Diarias_Scraper(log)
scrap.process('2017-11-01', '2017-12-01')
```

