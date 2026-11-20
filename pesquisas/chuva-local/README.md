# Chuva intensa em escala local

## 20 de novembro de 2026 · Primeira rodada

**Pergunta.** Quando o radar e os enlaces de micro-ondas das operadoras divergem, um filtro que considere a intensidade da chuva e a distribuição dos enlaces preserva melhor os picos reais que um limite fixo?

A chuva enfraquece o sinal de micro-ondas entre antenas. Esse efeito permite estimar quanto choveu ao longo do caminho. A combinação com radar pode melhorar o mapa de chuva já ocorrida e servir de insumo ao monitoramento de enxurradas urbanas. O piloto usa medições arquivadas e avalia apenas a estimativa de chuva.

Øydvin et al. compararam filtros fixos e propuseram testar limites adaptados à intensidade e à geometria da rede. No conjunto italiano, o radar sozinho teve desempenho melhor que algumas combinações sem filtro. O trabalho de Nielsen et al. já avaliou o ajuste por mediana móvel, que também merece entrar na comparação antes de propor um método novo. [Øydvin et al., especialmente §§ 4.7 e 5](https://doi.org/10.5194/hess-30-7007-2026) · [Nielsen et al.](https://www.sciencedirect.com/science/article/pii/S0169809524000103)

### O que foi executado

Rodei o método aditivo por distância inversa do pacote `mergeplg` 0.2.0, com até 70 enlaces vizinhos e os limites de diferença de 5 e 10 mm/h do estudo. A amostra pública OpenMRG cobre 22 a 29 de julho de 2015 em Gotemburgo, com 364 enlaces no arquivo, radar de 2 km e dez pluviômetros municipais. O teste compara as estimativas horárias da célula mais próxima com o pluviômetro. Os pluviômetros entram somente na avaliação. [Código do piloto](piloto_openmrg.py) · [Artigo do conjunto OpenMRG](https://doi.org/10.5194/essd-14-5411-2022) · [Pacote e exemplos](https://github.com/OpenSenseAction/mergeplg/tree/v0.2.0)

| Método | Erro absoluto médio, 1.910 pares | Com chuva, 382 pares | Com ≥5 mm na hora, 16 pares |
| --- | ---: | ---: | ---: |
| Radar | 0,203 mm | 0,860 mm | 5,614 mm |
| Correção aditiva, limite de 5 mm/h | 0,147 mm | 0,606 mm | 4,408 mm |
| Correção aditiva, limite de 10 mm/h | 0,141 mm | 0,593 mm | 3,940 mm |

Os dois limites produziram estimativas diferentes em 78 pares hora–pluviômetro, incluindo 14 dos 16 com pelo menos 5 mm. Esses 16 pares ocorreram em quatro datas. Algumas observações podem pertencer à mesma tempestade. O teste transcorreu em 38 segundos em CPU.

O piloto usou a intensidade de chuva pré-processada do primeiro sentido de cada enlace. Exigi metade das amostras de 10 segundos por hora para os enlaces e 60 minutos válidos por hora para os pluviômetros. Agreguei os volumes dos pluviômetros pelo fim de cada minuto e as taxas instantâneas de radar pelo horário da varredura. Escolhi 5 mm em uma hora como corte exploratório. A classificação de horários chuvosos no pré-processamento dos enlaces usa o próprio radar. Esse desenho pode reduzir a capacidade de recuperar chuva onde o radar indica zero. O piloto cobre um recorte do método publicado e ainda não compara um filtro adaptativo. [Pré-processamento da amostra](https://github.com/OpenSenseAction/opensense_example_data/blob/b4266fa5603a4791302b2b11fcff5d2ffc6cdee0/OpenMRG/notebooks/create_8d_OpenMRG_data.ipynb)

### Reprodução

Baixe os três NetCDF para um diretório local. Usei Python 3.12, `mergeplg==0.2.0`, `poligrain==0.4.0`, `netCDF4==1.7.2`, `xarray==2026.9.0`, `numpy==2.3.5`, `pandas==2.2.3` e `scipy==1.16.3`. [Radar](https://raw.githubusercontent.com/OpenSenseAction/opensense_example_data/b4266fa5603a4791302b2b11fcff5d2ffc6cdee0/OpenMRG/openmrg_rad_8d.nc) · [Enlaces](https://raw.githubusercontent.com/OpenSenseAction/opensense_example_data/b4266fa5603a4791302b2b11fcff5d2ffc6cdee0/OpenMRG/openmrg_cml_8d.nc) · [Pluviômetros](https://raw.githubusercontent.com/OpenSenseAction/opensense_example_data/b4266fa5603a4791302b2b11fcff5d2ffc6cdee0/OpenMRG/openmrg_municp_gauge_8d.nc)

```bash
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 python piloto_openmrg.py /caminho/dos/netcdf
```

### Parecer e ponto de retomada

**Vale continuar a triagem.** O custo de execução do piloto é baixo. O que decidirá a viabilidade de um artigo é o acesso a uma amostra maior de tempestades e a possibilidade de testar os limites em redes com densidades diferentes. Os arquivos completos e os notebooks do artigo estão indicados no Zenodo. As tentativas de acesso direto aos registros completos do OpenMRG e OpenRainER e ao registro dos notebooks retornaram HTTP 403 neste ambiente. Os recortes de oito dias de ambas as redes abriram, mas o recorte italiano contém sinais de rádio, sem estimativas de chuva prontas. [Dados e código do artigo](https://hess.copernicus.org/articles/30/7007/2026/#section7) · [Recorte OpenRainER](https://github.com/OpenSenseAction/opensense_example_data/tree/main/OpenRainER)

Numa retomada, dedicaria até duas horas a obter dados de mais tempestades e rodar o comparador fixo em OpenRainER com o radar bruto, preservando a independência dos pluviômetros. A triagem avança se houver eventos suficientes para reservar tempestades inteiras para avaliação. O teste compararia erro nos picos e falsos alarmes, com limiares definidos antes de abrir os eventos reservados. Se os recortes acessíveis forem insuficientes, a pesquisa deve mudar de tema. A pergunta metodológica que fica é se devemos separar a adaptação do filtro da detecção de chuva quando o radar indica zero.

O agendador disponível tem frequência máxima de uma execução por hora. Nenhuma rodada automática foi criada para o intervalo solicitado de 30 minutos.
