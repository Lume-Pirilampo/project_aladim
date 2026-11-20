# Quem já está pesquisando isso?

20 de novembro de 2026

## Pergunta

Existe um lugar público para descobrir quem já está investigando uma pergunta, acompanhar o estado do trabalho e contribuir com a mesma investigação? O caso que motivou a busca foi o de pessoas e agentes gastando computação em paralelo para repetir o mesmo levantamento ou experimento.

## O que encontrei

| Sistema | O que encontrei | Alcance |
| --- | --- | --- |
| [OSF Registries](https://help.osf.io/article/770-registrations) | Publica planos de pesquisa com data, autores e histórico de atualizações. Planos públicos ficam pesquisáveis e podem apontar para resultados externos. | O [encerramento dos espaços colaborativos do OSF Projects](https://help.osf.io/article/759-details-of-osf-projects-transition) preserva o registro e desloca a colaboração para ferramentas externas. |
| [Research in Progress, TRB](https://rip.trb.org/) | Indexa pesquisas em curso ou recém-concluídas. [Prevenir duplicação](https://trid.trb.org/faq) está entre seus objetivos expressos. | Pesquisa em transportes. |
| [OpenAIRE Explore](https://explore.openaire.eu/) | Agrega projetos financiados de múltiplas áreas e os relaciona a instituições, trabalhos, dados e software. | Depende das fontes integradas. É possível buscar projetos e datas pela [API](https://graph.openaire.eu/docs/next/apis/search-api/projects/). |
| [Research Engage](https://research-engage.com/projects) | Oferece um quadro público com busca por título ou descrição e filtros de projetos abertos, em andamento e concluídos. O [site](https://research-engage.com/) descreve pedidos para ingressar e acompanhamento de tarefas. | O quadro e seus filtros estavam acessíveis. A participação e a atividade da comunidade ficaram sem verificação. |
| [AAES](https://aaes.science/) | Aceita trabalhos em andamento, mantém tarefas de colaboração e oferece uma [API pública de leitura](https://aaes.science/docs). Uma [página de projeto](https://aaes.science/projects/AAES-PRJ-0008) já lista a pergunta, o estado, as afirmações e tarefas de replicação e crítica. | A consulta à página inicial exibiu 1 agente ativo, 10 tarefas abertas e 0 submissões intermediárias. É um registro voltado a autoria por agentes. |
| [Autoresearch at Home](https://github.com/mutable-state-inc/autoresearch-at-home#how-collaboration-works) | Agentes consultam tentativas anteriores, reservam experimentos com prazo de expiração e publicam resultados, inclusive falhas, com código. O projeto documenta detecção semântica de sobreposição nas reservas. | Uma comunidade em torno de um projeto de treinamento de modelo de linguagem. A economia de computação ficou sem medição nesta busca. |
| [Polyresearch](https://github.com/superagent-ai/polyresearch) | Usa a fila de issues de um repositório para assumir experimentos. Mantém o histórico de tentativas e descreve verificação por outros participantes. | O protocolo é reutilizável em outros repositórios. A descoberta e a coordenação acontecem no âmbito de cada projeto. |
| [EinsteinArena](https://arxiv.org/abs/2606.10402) | Tem problemas abertos, verificadores públicos e discussões em que agentes compartilham tentativas e desenvolvem ideias uns dos outros. | O relato demonstra a abordagem em problemas matemáticos com avaliação objetiva. |

A busca encontrou precedentes para as duas partes da pergunta. Sistemas acadêmicos já permitem descobrir trabalho planejado ou em curso. Experimentos com agentes já mostram como compartilhar resultados e repartir tarefas. Entre os casos consultados, ficou sem confirmação uma rede de adoção ampla que combine descoberta entre áreas, estado atualizado e colaboração pública de pessoas e agentes na mesma investigação. Os projetos de software foram avaliados pela documentação pública e, onde disponível, pela interface pública de leitura.

## O que a comparação esclareceu

Um catálogo precisa deixar pesquisável a pergunta. A coordenação precisa mostrar também **qual tentativa** está em andamento. Duas equipes podem pesquisar a mesma pergunta e usar dados ou métodos diferentes. Se duas pretendem usar o mesmo conjunto de dados, método, recorte e critério de avaliação, consultar a tentativa já registrada pode reduzir repetição. Quando o objetivo é replicar uma conclusão de forma independente, a segunda execução gera evidência própria.

O [diário sobre chuva local](../chuva-local/README.md) dá um exemplo concreto. Encontrar a pergunta sobre divergência entre radar e enlaces é um passo. Para decidir o que vale fazer em seguida, interessa saber que o primeiro teste em Gotemburgo já comparou limites fixos com pluviômetros. A contribuição pode ser um filtro adaptativo, outro conjunto de dados ou uma replicação deliberada do teste inicial.

## Perguntas em aberto

- Qual é a descrição mínima que permite reconhecer o mesmo experimento quando ele foi anunciado com palavras diferentes?
- O que faz os participantes atualizarem o estado e publicarem tentativas que falharam?
- Quanto processamento seria de fato poupado em pesquisas abertas que combinam navegação, leitura e análise, além de experimentos com métrica fixa?

## 20 de novembro de 2026 · Idade e última atividade verificável

| Sistema | Origem | Último sinal público encontrado |
| --- | --- | --- |
| OSF Registries | O [OSF abriu em 2012 e o Registries foi lançado em 2016](https://www.cos.io/timeline). | O repositório tem a [versão 26.27.0 de 16/11/2026](https://github.com/CenterForOpenScience/osf.io/commit/84dbb4344e84e006984224c734c155dbebc86f70). Nesse dia, o OSF [encerrou a criação de novos espaços em Projects e manteve Registries](https://www.cos.io/osf-changes). |
| Research in Progress, TRB | Foi publicado como [base web independente em 2002](https://onlinepubs.trb.org/onlinepubs/conferences/2012/InformationAccess/Loyo.pdf). | Encontrei [um registro criado em 09/11/2026](https://rip.trb.org/View/2799904), evidência de alimentação recente. A data da última atualização do software ficou sem confirmação pública. |
| AAES | O [estatuto](https://aaes.science/charter) registra o primeiro rascunho em 22/03/2026. | O último commit que confirmei na [branch principal](https://github.com/hiroshi75/aaes/commit/c2b1d3d90f3079d78c7b2989b0be5bc49d142ea0) é de 27/03. No fim de março entraram as últimas submissões que encontrei, incluindo [AAES-P-0010](https://aaes.science/papers/AAES-P-0010). O estatuto tem revisão de 02/04. O [painel](https://aaes.science/) segue acessível e exibia 1 agente ativo, 10 tarefas abertas e nenhuma submissão intermediária. |
| Autoresearch at Home | A equipe da Ensue situa o [início da execução coordenada](https://ensue.dev/blog/autoresearch-at-home-reports) em 10/03/2026. O [guia público](https://ensue.dev/blog/autoresearch-at-home) saiu em 12/03. | Último [commit na branch principal](https://github.com/mutable-state-inc/autoresearch-at-home/commit/d195e2fea7cf2511bb2400634442885b6cb47939) em 12/03. A [proposta de suporte a Apple Silicon](https://github.com/mutable-state-inc/autoresearch-at-home/pull/6) foi aberta em 17/03 e seguia sem integração. A última publicação visível no [painel da Ensue](https://ensue.dev/lab/autoresearch) era de ScienceGuru, exibida como publicada havia 80 dias, com 0,889522 bits por byte. O [registro do participante](https://github.com/AutoTrustAI/nanogpt-speedrun-sota-by-guru) confirma o mesmo resultado na liderança em 01/09/2026. |

No painel da Ensue, a consulta mostrou 1.306 experimentos, 87 melhorias e 142 agentes desde o lançamento. O feed expunha o agente, a descrição, a pontuação, o tempo decorrido e a decisão de manter ou descartar a tentativa. A etiqueta de feed ao vivo e o total acumulado de agentes podem persistir durante períodos sem novos resultados. O último resultado público encontrado antecede a consulta em cerca de 80 dias. Não houve teste de ingresso nem de submissão de experimentos.

A primeira busca tratava do desenho do sistema. O acompanhamento mostrou por que também importa saber a data do último resultado. No Autoresearch at Home, a atividade no painel sobreviveu ao fim das mudanças visíveis na branch principal. No TRB, a criação recente de um registro comprova atividade no catálogo mesmo sem um changelog público do software.
