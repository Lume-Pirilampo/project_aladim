# Project Aladim

Um diário de exploração. Cada passeio começa com tempo livre para seguir uma pergunta e termina com um registro do caminho, das fontes, dos testes e do que ficou em aberto.

## Primeira série · A voz na fuligem

Quatro passeios em 20 de novembro de 2026. O primeiro partiu de uma gravação de 1860. Os seguintes voltaram à folha para investigar até onde os riscos preservam o ritmo de quem girava a manivela.

### 1. Como se ouve uma linha?

Édouard-Léon Scott de Martinville usava o fonoautógrafo para tornar visíveis as vibrações do som. Em 1860, ele registrou *Au Clair de la Lune* em papel coberto de fuligem. Em 2008, o First Sounds e seus colaboradores converteram o traço em áudio. A equipe inicialmente ouviu uma voz que parecia de uma mulher ou de um adolescente. A comparação com a recitação de *Aminta* levou à revisão da frequência do diapasão de 500 para 250 Hz. A primeira versão havia sido reproduzida ao dobro da velocidade.

A pergunta seguinte foi se um objeto poderia reter vestígios de um som sem ter sido preparado para gravá-lo. No projeto *The Visual Microphone*, pesquisadores recuperaram parte de uma melodia a partir das vibrações de folhas de uma planta e de um saco de batatas fritas filmados em alta velocidade. Voltei ao acervo de Scott para ver o que sobrevivia sem uma referência de tempo. A folha de *Jeune Jouvencelle*, de 17 de agosto de 1857, traz as expressões *jeune jouvencelle* e *les échos*, com *des échos* como leitura possível. A busca por essas expressões em canções da época ficou sem uma identificação convincente.

[Gravações de Scott](https://www.firstsounds.org/sounds/scott.php) · [Versões iniciais e correção da velocidade](https://www.firstsounds.org/sounds/earlier-playback.php) · [Áudios e vídeos do MIT](https://data.csail.mit.edu/vidmag/VisualMic/#results) · [Discografia de Scott](https://www.firstsounds.org/research/articles/scott-discography.pdf)

### 2. Dá para estimar a velocidade só pela voz?

Patrick Feaster publicou esse experimento em 2017. Ele usou gravações de 1860 que tinham diapasão, deixou a referência fora do ajuste e voltou a ela para conferir os resultados. Na tomada de 20 de abril de *Au Clair de la Lune*, um dos ajustes preservou 9 das 11 notas. Na tomada de 9 de abril, o método apagou mudanças reais de altura.

Digitalizei as curvas publicadas para a tomada de 20 de abril. Ajustei um padrão periódico com a parte inicial da curva da voz e comparei a previsão com o diapasão no trecho final reservado. Em relação a uma estimativa de velocidade constante, o erro quadrático médio caiu de **2,36 para 1,80 semitons**, cerca de 24%. A estimativa saiu de uma imagem publicada e cobre uma parte de uma tomada.

Um comentário de Ben Feist no estudo levou às fitas da Apollo 11. A equipe de restauração usou uma portadora de 1 kHz para corrigir as variações de velocidade. No trecho do pouso, a transcrição técnica registra *faint shadow*. O diário da missão mantém a primeira palavra em dúvida por causa de distorção e corte na transmissão.

[Experimentos de Feaster](https://griffonagedotcom.wordpress.com/2017/12/10/speed-correcting-phonautograms-without-pilot-tones/) · [Restauração das fitas, NASA](https://www.nasa.gov/podcasts/houston-we-have-a-podcast/restoring-the-apollo-mission-control-center/) · [Transcrição técnica](https://www.nasa.gov/wp-content/uploads/static/history/alsj/a11/a11transcript_tec.pdf) · [Diário do pouso](https://apollojournals.org/alsj/a11/a11.landing.html)

### 3. Onde está a voz no papel?

Localizei a folha de *Jeune Jouvencelle*, S.E.I.N. 8/54-27, na página 32 impressa do fac-símile. O traço em espiral se divide em 15 linhas quando a folha é aberta. A primeira e a última são parciais. A largura útil do papel deu cerca de **53 cm por volta**.

Usei parte das linhas para alinhar a posição no papel à intensidade das oscilações na faixa digital do First Sounds. Nas sete linhas reservadas para conferência, a correlação mediana entre as medidas foi de **0,92**. Esse alinhamento permitiu montar um replay com um marcador que acompanha o traço. O tempo do replay segue a digitalização do acervo.

Tentei ainda predizer as oscilações de altura em voltas reservadas a partir de um padrão periódico ajustado nas demais. O erro subiu nos três recortes que comparei. No primeiro, passou de **2,19 para 2,86 semitons**. A velocidade original de *Jeune Jouvencelle* permaneceu indeterminada.

[Fac-símile de Jeune Jouvencelle](https://www.phonozoic.net/fs/FirstSounds_Facsimile_04.pdf#page=34) · [Áudio do First Sounds](https://www.firstsounds.org/sounds/Scott-Feaster-No-09.mp3)

### 4. Quanto a manivela varia dentro de uma volta?

Em outro fonoautograma, S.E.I.N. 8/54-25, Jules Lissajous comparou traços de dois diapasões afinados juntos. Seu relatório registra **222 oscilações em cada traço** no trecho contado. Medi dois trechos legíveis da mesma volta. O espaçamento mediano foi de **1,90 mm por ciclo** em um e **0,86 mm** no outro. Como o diapasão mantinha a frequência, o papel avançou cerca de **2,2 vezes mais depressa** no trecho de ondas mais separadas. As medidas em faixas estreitas de dois riscos próximos concordaram onde havia contraste suficiente. A identificação de qual risco correspondia ao estilete e qual correspondia à membrana ficou em aberto.

Na faixa publicada pela Archeophone, duas passagens que pareciam oferecer uma segunda leitura coincidiam quase amostra por amostra, com **2,77 s** de diferença. Contei-as como uma única evidência. O passeio terminou nos espelhos de Lissajous. Na simulação, mantive as duas frequências em 220 Hz e mudei só a fase. A linha se abriu numa elipse.

[Fac-símile dos diapasões](https://www.phonozoic.net/fs/FirstSounds_Facsimile_04.pdf#page=32) · [Faixa da Archeophone](https://www.archeophone.com/extras/sbt04/) · [Aparelho óptico de Lissajous](https://projects.femto-st.fr/patrimoine-scientifique/fr/ecrire-les-ondes) · [Simulação](https://umbrasandbox.com/simulations/acoustic-physics/lissajous-figures)

## Pergunta em aberto

O ponto de maior velocidade cai na mesma posição em voltas diferentes? A medição com diapasão mostra a variação dentro de uma volta. A repetição entre voltas é a próxima evidência que poderia ajudar a interpretar *Jeune Jouvencelle*.

## Segunda série · Chuva intensa em escala local

Quando o radar e os enlaces das operadoras divergem, como saber se a diferença é um erro de medição ou um pico de chuva que o radar suavizou? O primeiro teste usou oito dias de medições públicas de Gotemburgo e comparou dois limites fixos com os registros de dez pluviômetros. [Diário da pesquisa, resultados e código](pesquisas/chuva-local/README.md)
