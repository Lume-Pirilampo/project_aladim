# Validação de filtros para chuva intensa

## 20 de novembro de 2026 · Protocolo de continuação

A pergunta é se o limite para aceitar uma divergência entre radar e enlaces de micro-ondas deve depender da intensidade da chuva e dos enlaces vizinhos. Øydvin et al. identificam essa questão na discussão do artigo, depois de comparar limites fixos na Suécia e na Itália. A aplicação é a estimativa retrospectiva ou corrente de chuva em escala local, como insumo ao monitoramento de enxurradas. [Artigo, § 5](https://doi.org/10.5194/hess-30-7007-2026) · [Piloto anterior](README.md)

### Acesso e reuso

Encontrei a versão 1.0.0 dos notebooks dos autores e as tabelas usadas no artigo. A API do Zenodo respondeu para os dados completos e a publicação do código. O arquivo OpenMRG respondeu a uma requisição parcial e começou a ser baixado. Os três TAR usados para a Itália também responderam; tentar ler apenas os membros de junho a agosto de 2022 evita baixar os anos e os produtos de radar que o teste dispensa. A disponibilidade de cada mês ainda depende da integridade e da abertura dos arquivos. [Notebooks dos autores](https://github.com/OpenSenseAction/radar_adjustment_intercomparison/tree/v1.0.0) · [OpenMRG 1.1](https://zenodo.org/records/7107689) · [OpenRainER 2.0](https://zenodo.org/records/14731404)

As tabelas publicadas já mostram uma assimetria útil. O RMSE do método aditivo por distância inversa com limite de 10 mm/h foi 1,29 mm na Suécia e 3,23 mm na Itália. Sem o limite, foi 1,29 e 3,87 mm, respectivamente. São resultados dos autores no conjunto geral avaliado por eles. Nossa comparação vai perguntar o que acontece nas horas de chuva forte, com os métodos julgados nos mesmos pares hora–pluviômetro. [Tabelas originais](https://github.com/OpenSenseAction/radar_adjustment_intercomparison/tree/v1.0.0/data/metrics)

### Comparação definida antes de abrir os resultados

1. Usar radar bruto, enlaces e pluviômetros. Os pluviômetros ficam fora da correção. Usar a geometria de interseção dos autores para a chuva do radar ao longo do enlace e correção aditiva por distância inversa com até 70 vizinhos. A seleção da célula de radar mais próxima do pluviômetro deve ser idêntica para todas as estimativas.
2. Comparar radar, correção sem filtro e limites fixos de 5 e 10 mm/h, além de dois filtros exploratórios. No primeiro, o limite em mm/h é `B(r) = min(15, 5 × sqrt(1 + r / 2))`, em que `r` é a taxa de chuva do radar ao longo do enlace em mm/h. O valor cresce de 5 a 15 e chega a 10 com `r = 6`. A curva é uma hipótese de trabalho, sem ajuste aos pluviômetros.
3. No segundo filtro, dividir a diferença enlace–radar por `B(r)`. Com pelo menos oito outros enlaces válidos em 10 km, usar a mediana de até 12 vizinhos e aceitar desvios da mediana de até três escalas robustas, calculadas com 1,4826 vezes o desvio absoluto mediano. Limitar o desvio normalizado permitido ao intervalo de 0,5 a 2 e o valor absoluto do residual normalizado a 3. Com vizinhança insuficiente, usar o primeiro filtro.
4. Usar junho e julho de 2015 na Suécia para depurar o processamento e escolher, entre 5 e 10 mm/h, o comparador fixo pelo menor erro nas chuvas fortes. Agosto de 2015 fica reservado na Suécia. A rede italiana serve de transferência, com as mesmas regras e parâmetros. Se um recorte tiver sido visto para verificar unidades ou funcionamento, explicitar seu uso exploratório.
5. A métrica principal é o erro absoluto médio nos pares com chuva horária de pelo menos 5 mm, até 20 km do enlace mais próximo. Reportar também erro acima de 10 mm, viés, taxa de falsos alarmes a 5 mm e proporção de chuvas fortes detectadas, usando exatamente os mesmos pares válidos. Assim será possível ver se a redução de erro vem à custa de mais alarmes indevidos.
6. Para quantificar a incerteza, agrupar horas de chuva forte separadas por até seis horas no mesmo evento e reamostrar eventos inteiros, com os pares de pluviômetros mantidos dentro do evento. Se algum conjunto reservado tiver menos de dez eventos, tratar a comparação como piloto. Um ganho consistente pede redução de erro frente ao filtro fixo selecionado em cada rede, com aumento da taxa de falsos alarmes de no máximo 0,1 ponto percentual. Publicar a comparação mesmo se ela for desfavorável aos candidatos.

O protocolo compara filtros para a etapa de fusão. As estimativas de chuva nos enlaces seguem o pré-processamento publicado, que usa radar para separar períodos secos e chuvosos. A dependência entre as duas fontes e os limites da validação retrospectiva entram na interpretação.

### Primeira verificação · 14h13, horário de Brasília

O download integral do OpenMRG terminou e o MD5 coincidiu com o publicado (`4e4cdf6ced4d45a084c348f245b8d690`). Para o OpenRainER, foram obtidos e abertos os nove membros que cobrem três sensores e três meses. O processamento italiano gerou 2.207 horas na grade de avaliação, com 124 dos 151 enlaces após o controle de qualidade e 319 pluviômetros cadastrados. A extração por partes poupou o download dos outros meses e dos campos já corrigidos com pluviômetros.

No recorte sueco usado para desenvolvimento, a avaliação restrita às células dos pluviômetros reproduziu os mapas completos do `mergeplg` em oito horas de chuva intensa, nos três comparadores aditivos. A diferença máxima foi de 0,00000067 mm em 75 comparações por método, depois de alinhar os dados faltantes. Na primeira conferência houve uma diferença de 0,19 mm: em 28 de julho às 17h UTC, 803 células de radar estavam ausentes para a agregação completa. O pacote trata essas células como zero ao interpolar; o protocolo preserva o dado ausente e exclui os enlaces que cruzam células faltantes. Essa diferença de tratamento fica registrada para a comparação com os números publicados.

### Experimento secundário · Sensibilidade à densidade da rede

A comparação entre Suécia e Itália muda o clima, o radar e a rede ao mesmo tempo. Para isolar o papel da densidade, vou repetir a comparação removendo enlaces em cada rede, mantendo os mesmos pluviômetros, horas e tempestades. Serão 24 sequências de remoção aleatória com semente 20261120, com subconjuntos aninhados de 10%, 25%, 50% e 75% dos enlaces. A rede inteira será a referência de 100%. A análise vai usar agosto na Suécia e a janela italiana completa.

A remoção se aplica à interpolação e aos vizinhos do filtro. O conjunto de pluviômetros elegíveis é o da rede inteira, para a perda de cobertura aparecer no resultado. Vou medir a parcela de observações enlace–hora que ainda têm pelo menos oito outros enlaces válidos em 10 km e o erro dos filtros nessas redes reduzidas. A dispersão entre as 24 remoções descreve esse cenário artificial. Os intervalos de incerteza por tempestade ficam na comparação principal.
