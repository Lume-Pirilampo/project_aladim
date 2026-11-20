# Reprodução dos experimentos de Nova York

Usar Python 3.12. Extrair o arquivo OpenMesh 2.0.0 e fixar o código dos autores em `fc1e666bf26bb3eaf58096fc3f570ae26cf7bc46`. As estações ASOS do OpenMesh são a referência principal. O radar é o MRMS `RadarOnly_QPE_01H`, baixado separadamente da NOAA. O teste adicional usa o arquivo `pws_wu_os.nc`, com pluviômetros comunitários. Os CSVs publicados agregam estações por distância, método e período. [OpenMesh 2.0.0](https://doi.org/10.5281/zenodo.23283445) · [Código dos autores](https://github.com/drorjac/OpenMesh/tree/fc1e666bf26bb3eaf58096fc3f570ae26cf7bc46) · [Pluviômetros comunitários](https://doi.org/10.5281/zenodo.17508286)

Execute neste diretório e ajuste os três caminhos de dados. A fase mais longa é baixar os campos completos de radar, que entram em cache.

```bash
python -m pip install -r ../validacao/requisitos-validacao.txt requests==2.34.2 eccodes==2.50.1
export OPENMESH_REPO=/caminho/do/clone/OpenMesh
export OPENMESH_DATA=/caminho/do/arquivo/extraido/openmesh-2.0.0
export NYC_PWS=/caminho/para/pws_wu_os.nc
export PYTHONPATH="../validacao:$OPENMESH_REPO/src:$OPENMESH_REPO/tutorials/v2"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
catalogo="$OPENMESH_REPO/dataset/meta/radar_events.csv"

python obter_radar_nyc.py "$catalogo" radar --month 2024-05
python obter_radar_nyc.py "$catalogo" radar --month 2024-06
python preparar_nyc.py "$OPENMESH_DATA" radar/2024-05.nc radar/2024-06.nc maio-junho.nc
python avaliar_nyc.py maio-junho.nc 'NYC maio–junho' maio-junho.csv --protect-censored
python repassar_nyc_por_hora.py "$OPENMESH_DATA" maio-junho.nc replay --workers 5
python avaliar_nyc.py replay-0min.nc 'fim da hora' replay-0min.csv
python avaliar_nyc.py replay-30min.nc 'mais 30 min' replay-30min.csv
python avaliar_nyc.py replay-retrospectivo.nc 'retrospectivo' replay-retrospectivo.csv
python avaliar_pluviometros_comunitarios.py "$NYC_PWS" maio-junho.nc pws.csv radar/2024-05.nc radar/2024-06.nc
python checar_pluviometros_comunitarios.py "$NYC_PWS" maio-junho.nc pws-robustez.csv radar/2024-05.nc radar/2024-06.nc
```

Para obter os quatro casos da lista dos autores, execute `obter_radar_nyc.py` sem recorte de calendário, passe os quatro NetCDF resultantes a `preparar_nyc.py` e use `avaliar_nyc.py --catalog "$catalogo"` após os argumentos posicionais. Passe os mesmos NetCDF de radar junto ao arquivo de pares dos eventos para `avaliar_pluviometros_comunitarios.py` se quiser repetir a avaliação de estações comunitárias nos casos do catálogo. Repetir a preparação com `--without-blackout-fill` ou `--max-blackout-min 30` aplica as duas sensibilidades de preenchimento.

```bash
python obter_radar_nyc.py "$catalogo" radar --interval abr '2024-04-05 01:00' '2024-05-01 00:00'
python obter_radar_nyc.py "$catalogo" radar --interval jul '2024-07-01 01:00' '2024-07-14 23:00'
python preparar_nyc.py "$OPENMESH_DATA" radar/abr.nc radar/jul.nc abril-julho.nc
python calibrar_deteccao_nyc.py maio-junho.nc abril-julho.nc cortes.csv

python obter_radar_nyc.py "$catalogo" qualidade --quality --interval abr '2024-04-05 01:00' '2024-05-01 00:00'
python obter_radar_nyc.py "$catalogo" qualidade --quality --interval jul '2024-07-01 01:00' '2024-07-14 23:00'
python ponderar_qualidade_nyc.py abril-julho.nc qualidade.csv qualidade/abr.nc qualidade/jul.nc

python obter_radar_nyc.py "$catalogo" radar --interval mar1 '2024-03-01 01:00' '2024-03-22 18:00'
python obter_radar_nyc.py "$catalogo" radar --interval mar2 '2024-03-25 01:00' '2024-04-01 00:00'
python preparar_nyc.py "$OPENMESH_DATA" radar/mar1.nc radar/mar2.nc marco-sinal.nc
python preparar_nyc.py "$OPENMESH_DATA" radar/mar1.nc radar/mar2.nc marco-radar.nc --wet-from-radar
python comparar_classificador_nyc.py marco-sinal.nc marco-radar.nc classificador.csv 'NYC março, janelas reservadas'
python distancias_sinal.py maio-junho.nc abril-julho.nc distancias.csv
```

[Relato com critérios e resultados](../2026-11-20-nova-york.md) · [Métricas iniciais](nyc-metricas-iniciais.csv) · [Métricas complementares](nyc-metricas-complementares.csv) · [Cortes e falsos alarmes](nyc-cortes-de-alerta.csv) · [Disponibilidade de sinal](nyc_disponibilidade_mes.csv) · [Pluviômetros comunitários](nyc-pluviometros-comunitarios.csv)

O teste de transferência de cortes em pluviômetros comunitários usa os pares de maio–junho e de março já preparados acima.

```bash
python calibrar_alertas_comunitarios.py "$NYC_PWS" maio-junho.nc marco-sinal.nc pws-cortes.csv \
  --calibration-radar radar/2024-05.nc radar/2024-06.nc \
  --verification-radar radar/mar1.nc radar/mar2.nc
```
