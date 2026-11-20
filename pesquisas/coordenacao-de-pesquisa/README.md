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
