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

### Controle temporal adicional

Os dois filtros adaptativos permanecem congelados. O limite de 10 mm/h venceu o de 5 mm/h no desenvolvimento sueco (junho e julho) e será a comparação de referência. Agosto teve apenas quatro eventos pelo critério definido, com 33 pares de chuva forte. O filtro com vizinhos marcou erro de 1,501 mm contra 1,584 mm no limite fixo. A fusão sem filtro marcou 1,465 mm nesse recorte. Esse primeiro número, sozinho, permite apenas um parecer exploratório.

Antes de consultar as métricas italianas, iniciei o download de junho a agosto de 2021 para verificar se o resultado de 2022 se repete sob outra temporada na mesma rede. A comparação acrescenta variação temporal, e a Suécia já foi usada para congelar o comparador. Os campos de fusão publicados pelos autores também serão medidos sobre a mesma referência para situar a utilidade prática de trabalhar apenas com interpolação aditiva.

### Resultados reservados · Agosto sueco e verão italiano de 2022

| Rede e recorte | Eventos | Pares ≥5 mm | Radar | Fixo 10 | Intensidade | Intensidade e vizinhos |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Suécia, agosto de 2015 | 4 | 33 | 2,798 | 1,584 | 1,604 | 1,501 |
| Itália, junho a agosto de 2022 | 36 | 2.023 | 5,675 | 5,118 | 5,013 | 5,014 |

Valores de erro absoluto médio, em mm, nos pares hora–pluviômetro com pelo menos 5 mm registrados. Na Itália, a diferença do filtro por intensidade para o fixo foi −0,105 mm, com intervalo de 95% de −0,351 a +0,004 mm por reamostragem de eventos. Com vizinhos, o intervalo foi de −0,372 a +0,012 mm. O fixo detectou 83,44% das chuvas fortes, com 1.326 falsos alarmes. Os filtros adaptativos detectaram 82,20%, com 1.239 e 1.233 falsos alarmes. O ganho médio teve esse custo de detecção.

O filtro com vizinhos teve os oito vizinhos exigidos em 95,2% das observações elegíveis na Suécia e 10,6% na Itália. Nas 24 reduções a 50% da rede, o suporte mediano ficou em 82,7% na Suécia e 0,0% na Itália. Na Suécia, com 10% dos enlaces, o sinal da diferença mediana do filtro com vizinhos para o fixo passou de −0,083 mm para +0,080 mm. Os testes de redução mantiveram as mesmas horas e os mesmos pluviômetros. O sinal sueco descreve quatro eventos e é exploratório.

### Extensão definida para a temporada italiana de 2021

O filtro com vizinhos quase sempre recorre ao filtro por intensidade na rede pouco densa. A ideia a testar é permitir um raio de até 30 km, reduzindo a influência da vizinhança quando os vizinhos são distantes. Se o oitavo enlace válido estiver a uma distância `d8`, usar peso `w = min(1, (10 km / d8)²)`. Multiplicar a mediana local por `w` e misturar a tolerância local com a tolerância 1 do filtro por intensidade, com pesos `w` e `1 − w`. Permanecem o máximo de 12 vizinhos e o limite absoluto normalizado de 3. Com menos de oito vizinhos válidos em 30 km, usar o filtro por intensidade. A temporada de 2022 motivou a extensão; 2021 serve de verificação temporal com a regra congelada. Os resultados do protocolo original permanecem identificados como tais.

### Teste com o mesmo orçamento de falsos alarmes

Comparar todos os métodos com o corte de previsão de 5 mm mistura a qualidade da estimativa com a diferença de calibração. Em um teste operacional exploratório, manter 5 mm como referência observada e calibrar o corte de previsão de cada método para no máximo 25 falsos alarmes por 10 mil observações abaixo de 5 mm. Escolher o menor corte que atenda a esse orçamento, com desempate conservador, usando somente o verão italiano de 2022. Congelar os cortes e aplicá-los a 2021. Reportar a taxa de detecção, a taxa efetiva de falsos alarmes e a diferença de detecção frente ao fixo de 10 mm/h por reamostragem de eventos. Esse orçamento dá escala ao experimento. Os cortes são de avaliação meteorológica e não limiares de alerta de enxurrada.

### Filtros em krigagem com deriva externa

Nos 33 pares fortes do agosto sueco, o campo aditivo arquivado pelos autores reproduziu o erro de 1,584 mm do comparador local. O campo publicado de krigagem em blocos com deriva externa de radar (KED) teve erro de 1,223 mm, com nove falsos alarmes nos pares comuns, ante 18 do aditivo. O ganho de trocar o interpolador nesse recorte é maior que o ganho de mudar apenas o filtro aditivo.

Vou testar os filtros também no interpolador KED do próprio `mergeplg` nas células dos pluviômetros, com o variograma esférico publicado (alcance de 30 km, efeito pepita de 0,3, patamar parcial de 0,7), até 70 vizinhos e geometria dos enlaces em blocos ou pontos. As regras de exclusão são as mesmas já escritas. A verificação numérica contra o KED em mapa completo precede o uso como comparador. [Campos dos autores](https://doi.org/10.5281/zenodo.23367571)

### Extensão · Divergência entre as duas direções do enlace

A etapa de preparação combina duas estimativas de chuva entre o mesmo par de antenas. Quero testar se a discordância entre elas ajuda a identificar quando confiar menos no enlace. Špačková et al. já usaram discrepâncias entre enlaces colocalizados para estudar fontes de erro. Aqui o teste é se esse sinal melhora a fusão com o radar quando julgada por pluviômetros, mantendo o filtro fixo de 10 mm/h. [Špačková et al. (2023)](https://doi.org/10.5194/amt-16-3865-2023)

Com os dois sentidos disponíveis, usar `q = |R₁ − R₂| / sqrt(1 + (R₁ + R₂)/2)`. Comparar os erros do radar e dos enlaces curtos, com até 3 km, em pluviômetros a até 1 km do trajeto. Para evitar duplicar a referência de um pluviômetro, usar o enlace mais próximo que satisfaça esses limites, fixado antes de ler os horários. Dividir `q` em até 0,25, de 0,25 a 1 e acima de 1, e separar as intensidades observadas para reduzir a confusão entre discordância e volume de chuva.

No KED, aumentar o efeito pepita de um enlace para `0,3 × (1 + min(9, q²))` quando houver estimativas dos dois sentidos. Para uma única direção válida, manter 0,3, como no comparador. Essa ponderação testa se a informação redundante do enlace reduz erros sem precisar descartar observações adicionais. O filtro fixo e todo o resto do processamento ficam iguais. A temporada italiana de 2021 será usada sem ajustar esses parâmetros pelos seus resultados.

### Resultados da temporada italiana adicional

No verão de 2021, foram 43 eventos e 1.044 pares hora–pluviômetro com pelo menos 5 mm. No aditivo, o limite fixo deu erro de 4,369 mm. O filtro por intensidade marcou 4,344 mm, o de vizinhos 4,355 mm e o de alcance ampliado 4,352 mm. Os três intervalos de diferença incluem zero, e o erro acima de 10 mm foi maior nos três candidatos. O alcance de 30 km não melhorou os resultados em relação à versão por intensidade.

Ao calibrar os cortes de previsão em 2022 e aplicá-los a 2021, o filtro por intensidade detectou 852 de 1.044 chuvas fortes, contra 840 do limite fixo. Foram 15,56 contra 15,13 falsos alarmes por 10 mil observações sem chuva forte. A diferença emparelhada de detecção foi de 1,15 ponto percentual, com intervalo de cerca de 0,00 a 2,08 pontos. Nessa comparação, o radar sozinho detectou 748 casos com 10,11 falsos alarmes por 10 mil. O orçamento era igual na calibração, e as taxas realizadas mudaram na outra temporada.

O KED coincidiu com o mapa completo a menos de 0,0000004 mm em 75 comparações por geometria no recorte de conferência. Na Itália, o KED em blocos com limite de 10 mm/h deu 5,331 mm em 2022 e 4,960 mm em 2021. O filtro por intensidade deu 5,348 e 5,004 mm. A adaptação ensaiada no aditivo não transferiu para esse interpolador. Esses resultados reduzem a prioridade de perseguir a regra geométrica ensaiada; a incerteza medida pelos dois sentidos do enlace é uma hipótese diferente. [Código publicado](validacao/)
