# Recomeço do Fiscaliza: pipeline de dados abertos e site

Estado: aprovado a 20 de outubro de 2026 (estrutura e política de integração).

## Porque recomeçamos

O problema de fundo é a ingestão antiga. Lê a cópia XML dos dumps do parlamento.pt, corre 23 mapeadores escritos à mão, escreve linha a linha através do ORM em 230 tabelas e é comandada por três orquestradores diferentes, numa infraestrutura AWS pesada. Cada alteração no formato da fonte parte-a, e o site publicado mostrava números errados: 1446 deputados na XVII legislatura, que tem 230 lugares.

Os dados em si são pequenos. Todo o JSON ocupa 1,7 GB, e o DuckDB lê-o em segundos. Converter todas as iniciativas e intervenções (cerca de 1 GB de JSON) para Parquet demorou 5 segundos e deu 33 MB. É um problema de processamento em lote, e vamos tratá-lo como tal.

## Objetivos

- Um conjunto público, versionado e documentado de dados limpos sobre a Assembleia da República, reconstruído todos os dias a partir dos dumps oficiais, com a fonte em bruto no git para que cada alteração da AR seja um diff que se pode rever.
- Números que se podem defender. Cada tabela publicada tem testes que a ligam à fonte e a factos conhecidos, como os 230 lugares.
- Tudo comandado por CI/CD, sem servidor nem base de dados. O Fiscaliza é um dos consumidores. Custo de funcionamento nulo, ou perto disso.

## Fora dos objetivos

- Sem API em direto na v1. Quem quiser consultar pode apontar o DuckDB, o pandas ou o R aos ficheiros Parquet.
- Sem XML. Os dumps JSON e XML têm o mesmo conteúdo, e o JSON é mais simples de carregar.
- Sem correção histórica para além do que a fonte dá. Onde a fonte está incompleta, assinalamos em vez de corrigir à mão, exceto em pequenas tabelas seed que citam a sua fonte.
- O DAR (o Diário) fica fora da v1. Ver a secção sobre o DAR.

## Divisão dos repositórios

**Repositório de dados abertos: `rfsbraz/parlamento-aberto`.** Criado a 20 de outubro de 2026 como repositório privado, já é público. A primeira publicação de dados sai quando eu a ligar. Contém o código do pipeline, os modelos SQL, os testes, a documentação, o dicionário de dados e os dados em bruto da AR normalizados. Começa com um histórico novo. O CI corre o gitleaks em cada PR.

**Repositório do site.** O site do Fiscaliza vive num repositório à parte e só consome as publicações de dados.

**Como o site consome os dados.** O site nunca fala com o parlamento.pt. O seu passo de build descarrega a publicação de dados mais recente, verifica que a versão major do schema no manifest é uma que suporta e gera páginas estáticas e fragmentos JSON por legislatura a partir dos ficheiros Parquet. Um workflow agendado do site reconstrói-o uma vez por dia, depois da execução dos dados. Se a verificação do schema falhar, o build falha e o deploy anterior mantém-se. Não é preciso nenhum token entre repositórios.

## Dados em bruto no git

Os ficheiros em bruto da AR ficam no git como texto extraído e normalizado, nunca como ZIP, para que um PR de dados mostre os registos que mudaram. Um estudo de dimensionamento (20 de outubro de 2026) definiu a estrutura:

- As Iniciativas da XIII e da IX passam o limite de 100 MiB do GitHub, e a XVII tem 94 MiB ao fim de um ano, por isso um ficheiro por legislatura não serve.
- A ordem dos registos da AR é instável, e uma linha NDJSON por iniciativa pode ter 1,1 MB, que o GitHub não mostra.
- A estrutura por registo cresceu entre 22 e 43 KB por dia ao longo de 25 dias reproduzidos. Estimativa: 100 a 210 MB comprimidos ao fim de um ano, muito abaixo da recomendação de 5 GB do GitHub. O Git LFS não é necessário e esconderia os diffs.
- Os soft 404 são temporários (os 8 observados recuperaram todos em menos de uma hora). O servidor limita o tráfego entre cerca das 04:00 e as 06:00, hora de Lisboa, e serve gzip com cerca de 10% do tamanho.

**Estrutura.** Tudo fica em `data/`, organizado por conjunto de dados e legislatura, com as chaves ordenadas e o UTF-8 mantido tal como está.

- **Conjuntos de dados aninhados e com muitos registos** (Iniciativas e, provavelmente, AtividadeDeputado e Peticoes): um ficheiro JSON por registo, formatado e com as chaves ordenadas, em pastas agrupadas por id, por exemplo `data/iniciativas/XVII/377/377352.json`. Uma nova votação numa iniciativa aparece no PR como os campos da votação.
- **Conjuntos de dados planos** (Intervencoes, PerguntasRequerimentos, Agenda, tabelas da InformacaoBase e semelhantes): NDJSON com as chaves ordenadas, registos pela ordem do id natural, divididos em intervalos fixos de id ou de ano para que um registo nunca mude de ficheiro. Cada ficheiro fica abaixo dos 50 MB.
- Nenhum ficheiro se pode aproximar dos 100 MB. O CI faz falhar qualquer PR que acrescente um ficheiro com mais de 50 MB.
- `data/_meta/sources.lock.json` regista, por ficheiro da fonte: o SHA-256 do último ficheiro descarregado bom, a data em que foi descarregado, o número de registos, a impressão digital das chaves de topo e o estado de desatualização. É com ele que o relatório de alterações e as regras de validação comparam.

Descarregar ficheiros que não mudaram produz um resultado idêntico byte a byte, por isso não acrescenta nada ao histórico. Os ZIP do DAR e 67 ficheiros mais pequenos ainda têm de ser dimensionados; o PR de fetch mede-os primeiro.

## Onde ficam os dados publicados

Decisão: **GitHub Releases no repositório de dados abertos**, uma publicação por cada integração que altera dados, com a tag `data-AAAA-MM-DD` (com um sufixo se houver duas no mesmo dia).

Razões: gratuito e sem custos de saída de tráfego, junto do código e dos dados que os produziram, imutável e citável, e a "latest release" é um ponto de entrada estável. Estima-se que todos os marts em Parquet fiquem abaixo dos 200 MB. Com o repositório público, os runners alojados pelo GitHub não gastam minutos de Actions.

Cada publicação contém:
- um ficheiro Parquet por mart, mais um CSV comprimido com gzip de cada mart para quem usa folhas de cálculo;
- `manifest.json` com a versão do schema, a hora do build, o SHA do commit de dados de onde foi construída, o número de linhas por mart e por legislatura, e o SHA-256 e a data de descarga de cada ficheiro da fonte usado;
- um excerto `CHANGELOG.md` com as alterações ao schema.

Os snapshots em bruto deixam de ser arquivados como ficheiros das publicações. O histórico do git é o arquivo, e o SHA do commit no manifest chega para reconstruir qualquer publicação. O R2 e o Hugging Face não são usados na v1; o Hugging Face pode ser acrescentado mais tarde como espelho, num PR pequeno.

O site vai para o Cloudflare Pages (escalão gratuito, 20 000 ficheiros por deploy), com deputados, partidos e legislaturas pré-renderizados e as iniciativas e votações carregadas no browser a partir dos fragmentos.

## Licenças

**Termos da fonte.** A página de dados abertos do parlamento.pt diz que os dados "podem ser livremente reutilizados por qualquer instituição ou pessoa para a criação de novos conteúdos, devendo apenas ser mencionada a fonte (Assembleia da República)". Fonte: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx (verificado a 17 de outubro de 2026). A única condição é a atribuição.

**Dados: licença repartida** (`LICENSE-DATA`, 20 de outubro de 2026).

- Os ficheiros brutos da AR em `data/` são dados da AR reutilizados nos termos da AR, não sob uma licença nossa. A Lei n.º 26/2016, art. 19.º, n.º 5, pede que se mencionem a fonte e a data da última atualização e que a informação não seja alterada ([diariodarepublica.pt](https://diariodarepublica.pt/dr/legislacao-consolidada/lei/2016-106603618)).
- Os marts publicados e o dicionário de dados estão sob CC BY 4.0, com a AR creditada. A atribuição ("Fonte: Assembleia da República, dados abertos") e a data de atualização (`source_updated`, a data de recolha mais recente em `sources.lock.json`) vão no `manifest.json` e no comentário inicial de cada CSV, com a licença de cada mart.
- `data/ept_*` e tudo o que deriva da EpT ficam fora da CC BY: são republicados citando a EpT como fonte, ao abrigo da Lei n.º 52/2019, art. 15.º, n.º 1, e da Lei n.º 26/2016 (LADA), art. 21.º, n.º 1. Fica excluído apenas o NIF dos titulares. `release.ept_derived` marca um mart construído a partir de modelos ou seeds da EpT, e um teste falha se algum mart publicado o for.

**Código: MIT**, porque a AGPL desencoraja a reutilização de um pipeline pequeno. O repositório do site mantém a AGPL-3.0.

**Dados pessoais.** Biografias, datas de nascimento e registos de interesses são dados pessoais. Republicamos apenas o que a AR publica e indicamos um contacto para correções no README. Um custo de ter os dados em bruto no git: depois de o repositório ser público, remover um registo do histórico obriga a reescrevê-lo. Se a AR retirar um registo, apagamo-lo daí em diante, e só reescrevemos o histórico se um pedido o exigir.

## Pipeline

Um único pacote Python, corrido com `uv`, a usar DuckDB. Os modelos são ficheiros SQL simples corridos por ordem por um pequeno executor, com as descrições das colunas em YAML, que também geram o dicionário de dados. Sem dbt: cerca de 20 modelos não precisam dele.

1. **Descarga.** O `sources.yaml` lista o URL de cada conjunto de dados por legislatura. Os pedidos são sequenciais, pedem gzip, enviam um User-Agent claro e repetem com espera crescente. Um soft 404 é repetido dentro da mesma execução; se persistir, fica a última cópia boa e o ficheiro é marcado como desatualizado.
2. **Validação.** Não há ETag nem Last-Modified, por isso calcula-se o hash de cada ficheiro descarregado. Um ficheiro é rejeitado, mantendo a última cópia boa e ficando marcado como desatualizado com o motivo no lock e no relatório, se for HTML, não se conseguir ler, for `[]` ou `null` quando a última cópia boa tinha registos, ou tiver uma queda de mais de 5% no número de registos em relação a ela (#135). As fontes que são uma janela móvel (`rolling: true`, só a agenda) aceitam essa queda, mas põem o PR em espera, e as fontes com `merge: upsert` medem-na depois da junção (passo 3). Uma alteração no conjunto de chaves de topo deixa o ficheiro passar, mas põe o PR em espera. Cada execução compara também o lock com o de `main`, porque a comparação com o lock do ramo só assinala a queda na primeira execução que a vê: enquanto uma fonte tiver mais de 5% menos registos do que em `main`, o corpo do PR lista-a em "Row drops against main" e o PR fica com `hold: row-drop`. O `data-merge.yml` repete a verificação antes do merge.
3. **Normalização.** Os ficheiros aceites são escritos na estrutura acima. Os registos que desaparecem da fonte são apagados e contados como removidos, exceto nas fontes com `merge: upsert` (intervenções e iniciativas, #133). Nessas, o ficheiro da AR atualiza e acrescenta registos por id, os registos que deixou de fora mantêm-se e as linhas sem id são descartadas. A queda de mais de 5% é medida no total guardado depois da junção, o lock guarda também o total do ficheiro da AR (`source_records`) e o relatório indica quantos registos guardados faltam na fonte. Apagar esses registos exige `fetch --prune`, corrido à mão e revisto num PR; o workflow noturno nunca o usa.
4. **PR de dados.** Se algo em `data/` mudou, o workflow faz commit no branch `data/nightly` e abre ou atualiza um PR. A descrição traz o relatório de alterações: por conjunto de dados e legislatura, os registos acrescentados, removidos e alterados, mais os ficheiros desatualizados e há quanto tempo o estão.
5. **Política de integração.** Os PR de dados são integrados automaticamente quando todas as verificações passam. Um PR com uma queda de linhas acima de 5%, uma alteração de schema ou do conjunto de chaves, um novo conjunto de dados ou legislatura, ou um snapshot mais antigo do registo da XVII que agora contém um id fora da XVII (`hold: source-changed`, #23) recebe uma etiqueta `hold:`, a integração automática não é ativada e sou eu que o integro. Enquanto um PR em espera estiver aberto, as execuções seguintes acrescentam commits ao mesmo branch e atualizam o relatório, por isso nunca se faz force-push. Em todos os PR, o check `data-hold` compara os registos das fontes centrais no resultado da integração com os da base, por legislatura, e falha numa queda acima de 5% que o PR não registe com `- drift: <dataset> <legislature>: motivo` em `docs/data-changelog.md` (#126). Um PR que não mexe nos dados passa.
6. **Staging e marts na integração.** A integração em main dispara o build: um modelo de staging por conjunto de dados, que lê os ficheiros normalizados com uma lista explícita de colunas, para que diferenças de tipo entre legislaturas não possam alterar o schema; depois os marts; depois todos os testes de dados.
7. **Publicação.** Se os testes passarem, escrevem-se o Parquet e o CSV, constrói-se o manifest e cria-se a publicação. Se um teste falhar, não há publicação e a anterior continua a ser a mais recente.

A execução falha, o que me envia um email, se um ficheiro principal da legislatura atual (InformacaoBase, Iniciativas, Atividades, Intervencoes) estiver desatualizado há mais de 7 dias.

**Identidade do bot.** Os PR abertos com o `GITHUB_TOKEN` por omissão não disparam o CI, e as integrações feitas com ele não disparam o workflow de publicação. Os workflows precisam de uma GitHub App instalada no repositório (ou de um token fine-grained) guardada como secret do repositório. Sou eu que a crio e guardo; o valor nunca vai para o git nem para conversas.

**Horários (Europe/Lisbon, todos depois da janela lenta da AR, das 04:00 às 06:00).**
- Execução noturna: todos os dias depois das 06:00. Só a legislatura atual, que é sempre a mais recente no `sources.yaml` (hoje a XVII), por isso uma nova passa a atual sem alterar código.
- Sincronização completa: mensal, no dia 3 às 06:30, hora de Lisboa, todas as legislaturas, com o hash a saltar os ficheiros que não mudaram. A execução noturna não corre no dia 3.
- Manual: um input de `workflow_dispatch` corre a sincronização completa à mão, opcionalmente limitada a um conjunto de dados ou a uma legislatura.
- Execução de recuperação: por volta das 09:30, volta a descarregar só os ficheiros marcados como desatualizados.
- Descoberta: semanal, à segunda-feira às 08:00. As ligações novas dão origem a um PR em espera ao `sources.yaml`, ou a uma issue se precisarem de uma decisão.
- Reconstrução do site: todos os dias às 11:00.

A execução noturna e a sincronização completa partilham o mesmo branch, PR, relatório de alterações e regras de integração. Um PR de sincronização completa que altera legislaturas passadas recebe também uma etiqueta informativa `historical-change`, que por si só não o põe em espera.

## Primeiros marts

Os mapeadores antigos em `scripts/data_processing/mappers/` e os dois documentos de análise são a especificação dos campos. Onde discordam do JSON, prevalece o JSON e registamos isso no dicionário.

- **legislatures**, **sessions**, **electoral_circles**: a partir da InformacaoBase.
- **deputies**: uma linha por pessoa (`cadastro_id`), nomes e biografia a partir do RegistoBiografico.
- **mandates**: uma linha por deputado, por legislatura e por período de situação (Efetivo, Suplente, Suspenso e outras), a partir de `DepSituacao`. "Com lugar na data D" é uma consulta a esta tabela, não uma coluna.
- **parliamentary_groups** e **group_memberships**: a partir de `GruposParlamentares` e `DepGP`. As filiações abertas trazem a data da extração como data de fim em vez de nulo, por isso o staging trata uma data de fim igual ou posterior à data da extração como aberta.
- **coalitions**: um CSV seed mantido à mão (AD, CDU, PàF e outras) que faz corresponder as coligações eleitorais aos grupos que se sentam no parlamento, com cada linha a citar uma fonte. O antigo `coalition_detector.py` é a lista de partida.
- **initiatives** e **initiative_authors**: a partir das Iniciativas.
- **votes**: uma linha por id de votação, a partir dos arrays `Votacao` nos eventos das Iniciativas e nas Atividades, com resultado, data, reunião e uma indicação `unanimous`. Os ids de votação repetem-se entre eventos (30 708 registos, 30 700 ids distintos), por isso eliminamos os duplicados por id.
- **vote_group_positions**: lido do texto `detalhe`, uma linha por votação, grupo e sentido de voto (a favor, contra, abstenção, ausente). Os textos têm o aspeto `A Favor: <I>PS</I>, <I> PSD</I><BR>Contra:<I>PCP</I>`, e os mais recentes acrescentam os deputados que votaram de forma diferente como `2-PS, Carlos Silva (PS), Fátima Correia Pinto (PS)`. O parser retira as marcas, divide em `<BR>` e produz linhas por grupo mais uma contagem dos votos diferentes. Quando uma votação é unânime e não tem detalhe, produzimos linhas a favor para cada grupo com lugar nesse dia e marcamo-las com `inferred = true`.
- **vote_deputy_dissents**: as pessoas nomeadas nos mesmos textos, associadas ao `cadastro_id` pelo nome parlamentar e pelo grupo dentro da legislatura. Os nomes sem correspondência ficam com id nulo e são contados nos testes.
- **interventions**: a partir das Intervencoes, com o debate, o orador e a referência da publicação.
- **questions**: perguntas e requerimentos, a partir das PerguntasRequerimentos.
- **interests**: a partir do RegistoInteresses, nas versões que o mapeador antigo trata (v1 a v3).
- **plenary_attendance** e **plenary_attendance_summary**: as listas de presenças das reuniões plenárias, a partir da ComposicaoOrgaos, associadas ao `cadastro_id` pela legislatura, pelo nome parlamentar e pelo grupo. Cada código de presença tem uma categoria num seed (`seed_attendance_codes`), confirmada nas páginas de cada reunião no parlamento.pt. O resumo conta, por legislatura, pessoa e grupo, as reuniões e cada categoria em separado, com as reuniões solenes e comemorativas numa linha à parte. O motivo da falta, texto livre, não entra.

## Testes e prova das contagens

Os testes unitários correm sobre fixtures guardadas no repositório, na estrutura acima, para que os PR de código nunca dependam de descargas em direto. Os testes de dados correm em cada build e bloqueiam a publicação se falharem.

- **Lugares.** Uma tabela seed tem o número de lugares de cada legislatura com a sua fonte. Para cada legislatura e cada data da amostra, os deputados com uma situação Efetivo aberta têm de ser no máximo o número de lugares, e na data da extração da legislatura atual têm de ser exatamente esse número.
- **Resultados conhecidos.** Para a XVII, na extração de 2026-10-16, a distribuição de lugares tem de ser PSD 89, CH 60, PS 58, IL 9, L 6, PCP 3, CDS-PP 2, BE 1, PAN 1, JPP 1. Corresponde às eleições de 2025.
- **Cobertura do parser.** Cada texto `detalhe` é lido por inteiro pelo parser das votações, e cada código de grupo que encontra existe nos grupos dessa legislatura.
- **Ligações.** Cada id de autor, orador e deputado com voto diferente corresponde a um deputado, e os nomes sem correspondência ficam abaixo de um limite pequeno por legislatura.
- **Desvio.** O número de linhas por mart e por legislatura é comparado com a publicação anterior, e uma queda acima de 5% bloqueia a publicação, a menos que esteja registada no changelog.

**Verificado** (descarga de 17 de outubro, estudo de dimensionamento de 20 de outubro): a InformacaoBase da XVII tem 1446 registos de deputados, dos quais 230 têm uma situação Efetivo aberta com a distribuição acima, por isso o site antigo contava todos os candidatos. 28 941 dos 30 708 registos de votações têm um texto `detalhe`, usando só A Favor, Contra, Abstenção e Ausência. As Iniciativas da XVII (soft 404) e as Intervencoes da XVII (`[]`) a 17 de outubro tinham recuperado ambas a 20 de outubro. Não há ficheiro RegistoInteresses para a XVI nem para a XVII.

## O DAR fica para depois

O Diário (a partir da XI, em ZIP) é a fonte mais rica e a que dá mais trabalho, por isso vem depois da v1: um workflow mensal que extrai o texto de cada reunião para `dar_sittings` e `dar_pages`, depois de um estudo prévio sobre tamanho e formato.
