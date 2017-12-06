# transparencia_scraper
Projeto para captura de dados disponíveis pelo governo federal no portal de transparência: www.portaltransparencia.gov.br.

Alguns arquivos são disponibilizados diariamente e outros mensalmente em formato CSV.

Os dados são divididos em bases (pastas) como CPGF, BolsaFamiliaFolhaPagamento, BolsaFamiliaSacado, etc.

# Exemplo:

Segue um exemplo de como usar a classe:

```
import logging 
log = logging.getLogger(__name__)
scrap = Transparencia_Scraper()
scrap.process_schemas(process_copa=False)
```
