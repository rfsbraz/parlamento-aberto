# Lacunas conhecidas na fonte

O que a AR publica, à data da sincronização completa de 20 de outubro de 2026. São lacunas na fonte, não no pipeline, e não as corrigimos à mão. `test_intervention_coverage_is_pinned` em `tests/test_interventions_questions.py` fixa a primeira e a última data de reunião por legislatura, por isso, quando a AR preencher uma lacuna, o teste falha. Atualize o valor fixado e esta página em conjunto.

## Deputados e biografias

O RegistoBiografico e a AtividadeDeputado constam da página de cada legislatura, mas a maior parte desses ficheiros não tem os dados dessa legislatura (#23):

- RegistoBiografico: os ficheiros da Constituinte, I-A, I-B e IV a XVI, tanto em JSON como em XML, são cópias mais antigas do registo da XVII: as mesmas 339 pessoas, com conteúdo mais antigo (335 pessoas em `RegistoBiograficoI`). Só a Constituinte, a II e a III têm ficheiros reais, todos no formato mais antigo: `RegistoBiograficoII/III_json.txt`, listados na página I Legislatura, com 432 e 454 pessoas, e o mais antigo dos dois ficheiros `RegistoBiograficoConstituinte.xml` na página da Constituinte (530 619 bytes, 313 pessoas), o único ficheiro lido como XML (`format: xml`, #28). A XVII é o registo atual.
- AtividadeDeputado: todos os ficheiros são cópias da lista da XVII, com as mesmas 1446 pessoas marcadas como XVII e uma data de extração mais antiga do que a da XVII. A II e a III vêm de `AtividadeDeputadoII/III_json.txt`, na página I Legislatura. A IV a IX têm alguma atividade datada no seu próprio período; a Constituinte, a I-A e a I-B não têm nenhuma.
- Estas cópias mais antigas são descarregadas e o seu hash é calculado, mas não são guardadas (`copy_of: XVII` no `sources.yaml`): o RegistoBiografico da Constituinte, I-A, I-B e II a XVI, e a AtividadeDeputado da Constituinte, I-A, I-B, II e III. A verificação é feita só pelos ids, porque o conteúdo é, por natureza, mais antigo do que o da XVII. Se alguma vez uma delas tiver um registo cujo id não está na XVII, o PR de dados recebe `hold: source-changed`. A AtividadeDeputado da IV à XVI continua guardada, por agora.

O mart `deputies` tira os campos biográficos da legislatura mais recente com um registo da pessoa e indica-a em `biography_legislature`. Pessoas nas listas de cada legislatura (InformacaoBase) com biografia, nos dados de 20 de outubro de 2026:

| Legislatura | Pessoas | Com biografia |
|---|---:|---:|
| Constituinte | 313 | 313 |
| I-A, I-B | 565 | 349 |
| II | 440 | 438 |
| III | 459 | 458 |
| IV | 417 | 249 |
| V | 417 | 172 |
| VI a XVI | 459 a 1513 | 56 a 263 |
| XVII | 1446 | 339 |

O registo mais antigo da Constituinte tem datas de nascimento para 38 das suas 313 pessoas.

Não usado: `AtividadeDeputadoCons.xml`, na página da Constituinte (267 833 bytes, ligação para `fich=AtividadeDeputadoX.xml`), é servido corrompido. Vem como `text/xml`, mas não é XML, gzip nem zip. Não se lê nenhum ficheiro de atividade da Constituinte.

### Uma só lista para a I-A e a I-B (#85)

A AR publica o mesmo `deputados.ndjson` nas pastas I-A e I-B da InformacaoBase, igual byte a byte, com todas as situações e grupos da legislatura I, de 1976-06-03 a 1982-03-03. As datas de cada parte vêm do DetalheLegislatura: a I-A vai de 1976-06-03 a 1980-01-02 e a I-B de 1980-01-03 a 1980-11-12.

Nos marts `mandates` e `group_memberships`, cada parte fica só com os períodos que se sobrepõem às suas datas (`legislatures.start_date` e `end_date`). As datas não são cortadas: um período de 1979-06-01 a 1980-03-01 fica nas duas partes com as datas publicadas pela AR. O raw continua igual ao que a AR publica. Nos dados de 21 de outubro de 2026, `mandates` passa de 893 linhas em cada parte (564 pessoas) para 626 linhas e 486 pessoas na I-A e 382 linhas e 326 pessoas na I-B; `group_memberships` passa de 755 linhas em cada parte para 429 na I-A e 326 na I-B.

A regra só se aplica à I-A e à I-B. `test_i_a_and_i_b_deputies_files_are_identical` em `tests/test_constituinte_parts.py` confirma que os dois ficheiros continuam iguais; se a AR passar a publicar uma lista por parte, o teste falha e a regra é revista.

## Intervencoes

Não há ficheiro publicado para a Constituinte, a I (I-A, I-B) nem a III.

| Legislatura | Datas da legislatura | Primeira e última reunião com intervenções | Lacuna |
|---|---|---|---|
| II | 1980-11-13 a 1983-05-30 | 1980-12-10 a 1982-04-25 | Só 98 registos. Nada depois de abril de 1982, e nenhuma reunião entre 1981-04-25 e 1981-12-12 nem entre 1981-12-12 e 1982-04-01. |
| IV | 1985-11-04 a 1987-08-12 | 1985-11-04 a 1986-10-31 | Nada nos últimos 9 meses. |
| VII | 1995-10-27 a 1999-10-24 | 1996-10-16 a 1999-10-01 | Nada no primeiro ano, e nenhuma reunião entre 1997-10-03 e 1998-09-16. |
| XII | 2011-06-20 a 2015-10-22 | 2013-09-16 a 2015-10-21 | Nada antes de setembro de 2013, cerca de dois anos. |
| XIV | 2019-10-25 a 2022-03-28 | 2019-10-25 a 2022-03-22 | Nenhuma reunião entre 2020-09-10 e 2021-09-15. |

Todas as outras legislaturas (V, VI, VIII a XI, XIII, XV, XVI) vão das primeiras semanas até cerca de seis semanas antes do fim, sem nenhum período de mais de 100 dias sem reuniões, exceto a primavera de 1992 na VI (1992-04-09 a 1992-07-27).

A XVII, em curso, deixou de ter lacuna na sincronização de 22 de outubro de 2026: a AR passou a publicar 7937 intervenções em 115 reuniões, de 2025-06-03 a 2026-09-18, e o período mais longo sem reuniões são as férias de 2026-07-17 a 2026-09-09. Até à sincronização de 21 de outubro só havia 81 registos, das reuniões de 16 e 18 de setembro de 2026.

A AR publica também 160 registos de Intervencoes com todas as chaves a nulo, na V, XI, XIV, XV, XVI e XVII (47 na XVII). O staging mantém-nos para que as contagens batam com `sources.lock.json`. O mart `interventions` exclui-os.

## PerguntasRequerimentos

Os ficheiros começam na VI. Não há nada publicado para as legislaturas anteriores.

28 perguntas têm uma data de envio (`DataEnvio`) cujo ano fica fora da sua legislatura, por exemplo 0024, 2208 ou 2909. A maior parte são gralhas da data de entrada. O mart `questions` guarda o valor publicado em `sent_date_raw`, põe `sent_date` a nulo e `sent_date_invalid` a verdadeiro. Um requerimento da VII (id 16560) não tem autores.

## Os seis ficheiros extra listados na legislatura I (#18)

Estas são conclusões sobre ficheiros que o `sources.yaml` deixa de fora, não lacunas no pipeline. Só contagens e ids; não se copia aqui nenhum dado pessoal.

As páginas "I Legislatura" de três secções listam seis ficheiros JSON cujos nomes dizem II ou III. As ligações e os tamanhos são diferentes dos ficheiros com o mesmo nome nas páginas da II e da III. Em cada página "I Legislatura" estão junto a ficheiros `II.xml` e `III.xml` com os mesmos nomes, sem título nem nota que os explique.

Descarregados a 20 de outubro de 2026 (um pedido cada, sequenciais, com gzip):

| Listado na I | Bytes | SHA-256 (primeiros 16) |
|---|---:|---|
| `AtividadeDeputadoII_json.txt` | 1 616 466 | `bee91d796d68cc0f` |
| `AtividadeDeputadoIII_json.txt` | 2 198 748 | `a467d185b52e7b42` |
| `RegistoBiograficoII_json.txt` | 456 728 | `bd44852b3c2f0347` |
| `RegistoBiograficoIII_json.txt` | 498 226 | `1dd5ab65b203412d` |
| `OrgaoComposicaoII_json.txt` | 315 438 | `9bdd7714a6a40e02` |
| `OrgaoComposicaoIII_json.txt` | 336 853 | `0d4ac781fa337a87` |

Os seis usam um formato mais antigo: XML convertido para JSON, com uma chave `?xml`, um único elemento raiz (`ArrayOfAtividadeDeputado`, `RegistoBiografico`, `OrganizacaoAR`) e nomes de campos em camelCase (`depCadId`, `cadId`). Os ficheiros nas páginas da II e da III, e todos os outros ficheiros JSON do `sources.yaml`, usam o formato atual: uma lista ou um objeto no topo, com nomes em PascalCase.

### OrgaoComposicaoII e III: cópias mais antigas, continuam excluídas

Têm dados da II e da III, os mesmos dos ficheiros nas páginas da II e da III, mas em menor quantidade:

| | Listado na I | Na página da II ou da III | Em comum |
|---|---:|---:|---:|
| II: membros do plenário (`depCadId`) | 432 | 440 | 432 |
| II: comissões | 30 | 30 | |
| II: última data | 1983-05-31 | 1983-05-30 | |
| III: membros do plenário | 454 | 459 | 454 |
| III: comissões | 32 | 32 | |

Todos os ids de membros dos ficheiros extra estão também no ficheiro atual, que tem mais alguns. Resultado (b) em #18: uma exportação mais antiga dos mesmos dados. Continuam fora do `sources.yaml`.

### AtividadeDeputadoII/III e RegistoBiograficoII/III: a única cópia dos dados da II e da III

Estes têm registos que faltam nos ficheiros das páginas da II e da III:

| | Listado na I | Na página da II ou da III | Em comum |
|---|---:|---:|---:|
| AtividadeDeputado II: deputados | 432, todos com `legDes` II | 1446, todos com `LegDes` XVII | 2 |
| AtividadeDeputado II: datas | 3479, de 1980-11 a 1983-05 | nenhuma antes de junho de 2025 | |
| AtividadeDeputado III: deputados | 454, todos `legDes` III | 1446, todos `LegDes` XVII | 4 |
| AtividadeDeputado III: datas | 6127, de 1983-05 a 1985-11 | nenhuma antes de junho de 2025 | |
| RegistoBiografico II: pessoas (`cadId`) | 432 | 339 | 2 |
| RegistoBiografico III: pessoas | 454 | 339 | 4 |

A II decorreu de novembro de 1980 a maio de 1983 e a III de maio de 1983 a novembro de 1985, o que corresponde aos ficheiros extra. Os ficheiros nas páginas da II e da III trazem antes a lista atual de deputados e o registo atual (ver abaixo). Resultado (c) em #18: estes quatro ficheiros são os dados da II e da III. As listas `RegistoInteresses` dentro dos dois ficheiros RegistoBiografico estão vazias.

### Relacionado: a AtividadeDeputado e o RegistoBiografico no formato atual não são por legislatura

Verificado nos 20 ficheiros de cada um, na descarga de 20 de outubro:

- Todos os ficheiros AtividadeDeputado, da Constituinte à XVII, têm os mesmos 1446 registos indexados por `Deputado.DepCadId`, todos com `Deputado.LegDes` XVII. Só a X a XVII têm entradas de atividade marcadas com a sua própria legislatura. A Constituinte, a I-A, a I-B, a II e a III não têm datas antes de junho de 2025.
- Todos os ficheiros RegistoBiografico têm entre 335 e 339 pessoas, e a união dos 20 ficheiros dá 339 ids. O registo é o mesmo pequeno conjunto, seja qual for a página de legislatura em que está.

Assim, os deputados e as biografias por legislatura das legislaturas antigas não estão nos ficheiros no formato atual. Para a II e a III estão nos ficheiros extra acima. Para as outras legislaturas antigas, os ficheiros `.xml` de cada página podem ser a fonte, o que não foi verificado.

### Decisão pendente

Acrescentar os quatro ficheiros da II e da III precisa de suporte no fetcher que ainda não está em main:

- um caminho com pontos até à lista de registos (`ArrayOfAtividadeDeputado.AtividadeDeputado`, `RegistoBiografico.RegistoBiograficoList.pt_ar_wsgode_objectos_DadosRegistoBiograficoWeb`), com os ids `deputado.depCadId` e `cadId`;
- uma chave de fonte que não colida com as entradas `II` e `III` no formato atual, por exemplo `part: xml`, o que dá `atividade_deputado/II-xml`;
- e uma escolha sobre se os ficheiros da II e da III no formato atual, que só repetem a lista da XVII, ficam sequer no `sources.yaml`.

Nenhum dos seis ficheiros tem entrada no `sources.yaml`. As entradas dos quatro ficheiros (c), e um comentário a registar que os dois ficheiros OrgaoComposicao ficam de fora, vão para o #23.

## RegistoInteresses

Todos os ficheiros RegistoInteresses, da Constituinte à XV, listam as mesmas 1446 pessoas: as listas da XVII, o mesmo conjunto da AtividadeDeputado. As pessoas que não estão nas listas da XVII não têm declarações aqui. A XVI e a XVII não têm ficheiro: as declarações passaram para a Entidade para a Transparência. A XVI e a XVII vêm da EpT, com `source = 'ept'`, e só são republicadas depois de a EpT responder: ver a secção seguinte e [sources/ept.md](sources/ept.md).

- A Constituinte a X não trazem nenhuma declaração, só a lista de pessoas (V3 sem `RecordInterests`). A Constituinte, I-A, I-B e II a X são idênticas byte a byte; a I difere em 17 registos.
- As declarações estão na XI (V1, 24), XII e XIII (V2, 43 e 61), XIV (V3, 111 declarações de 56 pessoas, e V5, 15) e XV (V5, 98). Cada uma indica a legislatura do seu próprio ficheiro.
- A V1 publica as atividades como um único campo de texto livre, não como lista. A V1 e a V2 publicam os apoios, os serviços e as outras situações como texto livre, que muitas vezes diz "Nada a declarar": 104 das 129 outras situações, 108 dos 151 serviços e 62 dos 255 apoios. Ficam tal como publicados.
- As datas são texto livre: um ano, um mês, um dia em ISO ou com o dia primeiro, ou um período. `start_date` e `end_date` só são preenchidos para datas ISO completas (1285 dos 2782 itens têm `start_date`); o texto publicado está nas colunas `_raw`.
- A V5 publica `Remunerada` como `N` ou `0`, nunca `S`, por isso `is_paid` é nulo para `0`. A V3 publica um código `Type` (0, 1 ou 2) que a AR não documenta; fica como `type_code`.

`test_full_data_declarations_are_pinned` em `tests/test_interests_coalitions.py` fixa o número de declarações por legislatura e formato.

## Registo de interesses da EpT (XVI e XVII)

As declarações da XVI e da XVII vêm da API pública da Entidade para a Transparência e entram em `interest_declarations` e `interests` com `source = 'ept'`. Diferenças face aos dados abertos da AR:

- Não há dedup entre fontes. A entidade 510 também tem declarações da XIV e da XV, que a AR já publica; nos marts só entram as da XVI e da XVII, e as outras ficam só em staging.
- Só entra o separador 4 (registo de interesses). O separador 2 (dados pessoais) e o separador 3 (rendimentos e património) nunca são guardados, nem os anexos.
- A secção de filiação ou funções em entidades de natureza associativa nunca é lida nem guardada, por isso não há `category = 'association'` (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)).
- A EpT não tem id da AR. O `cadastro_id` vem de `seed_ept_holders`, pela correspondência de nomes com a InformacaoBase e correções à mão. Um titular sem correspondência fica com `cadastro_id` nulo.
- A EpT guarda as versões: uma declaração substituída ou modificada fica como linha própria, com `declaration_state` replaced ou modified e `is_current` falso. Para contar uma declaração por titular e cargo, filtre `is_current`.
- A EpT publica a Remuneração como `1` ou `0` sem dizer o que significam, por isso `is_paid` fica nulo e o valor publicado fica em `paid_raw`.
- A EpT não publica exclusividade, data de alteração do cargo nem data de versão: `is_exclusive`, `position_changed_date` e `version_date` ficam nulos. A participação social vem em `share_value_eur` e `share_pct`, não em `share`.
- O detalhe dos serviços prestados ao abrigo de segredo profissional não é público (Lei n.º 52/2019, art. 17.º, n.º 2); só fica `is_professional_secrecy`.
- As datas da EpT vêm em UTC e são convertidas para o dia em Europe/Lisbon; o valor publicado fica nas colunas `_raw`.
- Licença: as linhas da EpT não estão cobertas pela CC BY 4.0. São republicadas citando a EpT como fonte, ao abrigo da Lei n.º 52/2019, art. 15.º, n.º 1, e da Lei n.º 26/2016 (LADA), art. 21.º, n.º 1 (`LICENSE-DATA`, ponto 3). Enquanto os dados da EpT não estiverem em `data/`, ficam fora dos ficheiros publicados e o `manifest.json` conta-as em `excluded_sources`.

## Votações

Pelo menos 1130 votações em plenário, à data de 21 de outubro de 2026, não são unânimes e não têm detalhe (`detalhe`), por isso o registo publicado não diz como votou cada grupo. 791 vêm das Iniciativas e 339 das Atividades, espalhadas por todas as legislaturas da I à XVII. 445 também não têm descrição. Ficam em `votes` com o seu resultado, mas não têm linhas em `vote_group_positions` nem em `vote_deputy_dissents`, e não se infere nada para elas. `test_non_unanimous_votes_without_detail_are_pinned` em `tests/test_committee_votes.py` verifica que não descem abaixo deste número; novas votações da AR só o podem aumentar.

Pelo menos 4705 votações em comissão, à data de 21 de outubro de 2026 (48% das 9723), também não são unânimes nem têm detalhe, em 111 comissões da VIII à XVII, a maior parte na XII (1504) e na XIII (1691). 2562 não têm descrição. 638 dizem "sem votos contra" na descrição, o que não diz que grupos votaram a favor ou se abstiveram, por isso não se infere nada a partir daí. Ficam em `votes` sem linhas por grupo. O mesmo teste verifica este mínimo.

A comissão 8331 (Comissão de Agricultura e Pescas, XV) tem 27 votações entre 2022-04-26 e 2024-01-04. A ComposicaoOrgaos da XV publica a comissão e as suas 116 reuniões, mas o histórico de membros (`HistoricoComposicao`) está vazio. Nenhuma das 27 votações precisa de linhas inferidas: 23 têm detalhe e 4 não são unânimes. `test_unanimous_committee_votes_have_a_composition` falha, indicando a comissão e a votação, se uma votação unânime em comissão que precise de linhas inferidas calhar numa comissão sem membros.

## Presenças no Plenário

O mart `plenary_attendance` lê as listas de presenças de `composicao_orgaos/<legislatura>/Plenario.Reunioes.ndjson`. Nos dados de 20 de outubro de 2026:

| Legislatura | Reuniões | Com lista de presenças | Linhas |
|---|---:|---:|---:|
| Constituinte a IV | 132 a 417 cada | 0 | 0 |
| V | 419 | 1 | 234 |
| VI | 375 | 374 | 86 019 |
| VII | 406 | 406 | 91 526 |
| VIII | 224 | 224 | 51 517 |
| IX | 269 | 269 | 61 871 |
| X | 468 | 468 | 107 640 |
| XI | 155 | 155 | 35 650 |
| XII | 469 | 469 | 107 868 |
| XIII | 413 | 413 | 94 990 |
| XIV | 197 | 197 | 45 310 |
| XV | 192 | 192 | 44 160 |
| XVI | 103 | 103 | 23 690 |
| XVII | 125 | 125 | 28 750 |

São 779 225 linhas, cerca de 230 por reunião (quem tinha lugar, substitutos incluídos). Não há listas antes da VI, além de uma reunião da V. A partir da VII, todas as reuniões têm lista. `test_rows_and_meetings_per_legislature_match_the_source` em `tests/test_plenary_attendance.py` fixa as linhas e as reuniões por legislatura. Se a AR acrescentar listas, o teste falha: atualize o valor fixado e esta tabela em conjunto.

Os dados abertos não têm legenda para os códigos de presença (`siglaFalta`), e a documentação da AR do ficheiro OrgaoComposicao só diz "Sigla da Falta do Deputado". Os significados em `seed_attendance_codes` vêm da comparação, deputado a deputado, entre o código nos dados abertos e o rótulo da página de cada reunião no parlamento.pt (`DetalheReuniaoPlenaria.aspx?BID=<meeting_id>`), em 8 reuniões de 2009 a 2026 consultadas a 20 de outubro de 2026, e da [Resolução da AR n.º 21/2009](https://www.parlamento.pt/Legislacao/Documents/Legislacao_Anotada/RegimePresencasFaltasPlenario.pdf), que aprova o regime de presenças e faltas ao Plenário. Cada linha do seed cita a reunião onde o código foi confirmado. As páginas mostram, por exemplo:

- PP e PT como Presença (P). O PP usou-se de 1991 a março de 2009.
- CO como Presença em Comissão autorizada pelo PAR, ME e MP como Ausência em Missão Parlamentar (AMP).
- FIJ, FAJ e QVJ como Falta Justificada (FJ).
- QV como Falta ao Quórum de Votação.
- FA só como Falta, sem a indicar justificada nem injustificada.

Não sobra nenhum código por confirmar. Se a AR publicar um código novo, o build para com o erro `attendance code not in seed_attendance_codes`.

O FA é uma falta que a AR ainda não classificou. O prazo para a justificar é de cinco dias parlamentares (n.º 11 e 12 da resolução), mas há FA com vários meses. O mart conta um FA como `pending` (por justificar) enquanto a reunião tiver menos de 60 dias na data de atualização dos dados (`source_updated`, a data em que o ficheiro da AR foi recolhido com alterações pela última vez, em `sources.lock.json`), e como `unclassified` (não classificada) a partir daí. Nunca o conta como falta injustificada. Nos dados de 20 de outubro de 2026, a XVII tem 34 FA (27 por justificar e 7 não classificadas) e 42 QV. Há quem conte 40 FA e 43 QV: são as linhas com data a partir de 1 de janeiro de 2025, que somam 6 FA e 1 QV da XVI. `test_xvii_fa_and_qv_counts_are_pinned` fixa os dois números.

As listas trazem o motivo da falta (`motivoFalta`), um texto que inclui doença, parentalidade, luto e assistência à família. Fica nos dados brutos tal como a AR o publica, mas não entra no staging nem nos marts.

## Contagem de lugares

As contagens de lugares por dia da Constituinte à VI estão sobrestimadas. Em alguns dias, `seated_on(d)` devolve mais deputados do que os lugares da legislatura, porque a fonte não fecha alguns períodos de substituição (#27). Se contar deputados por data nessas legislaturas, espere valores acima do real.

- A Constituinte a IV não registam suspensões, e a V e a VI só registam algumas. Quando um deputado regressa, muitas vezes nada termina o período do substituto, por isso ambos continuam efetivos até à data de fim publicada do substituto, às vezes o fim da legislatura.
- No início de uma legislatura ou de um novo governo, alguns deputados mantêm um período Efetivo ao mesmo tempo que os substitutos que tomaram posse por eles no primeiro dia, sem suspensão registada.

Não se infere nada para corrigir isto: a fonte não diz que substituto substituiu quem. Da VII à XVII, o número de deputados com lugar nunca ultrapassa o do seed de lugares, uma vez tratados os dias de troca. `test_seated_never_exceeds_seats_on_full_data` em `tests/test_seats.py` verifica cada dia de cada legislatura, de forma estrita para a VII a XVII, e fixa o máximo e os dias acima para a Constituinte a VI, com os dados de 20 de outubro de 2026:

| Legislatura | Lugares | Máximo com lugar | Dias acima |
|---|---:|---:|---:|
| Constituinte | 250 | 250 | 0 |
| I-A | 263 | 271 | 1178 |
| I-B | 250 | 254 | 249 |
| II | 250 | 257 | 891 |
| III | 250 | 258 | 887 |
| IV | 250 | 256 | 639 |
| V | 250 | 254 | 1346 |
| VI | 230 | 232 | 746 |

Se a AR fechar esses períodos, o teste falha. Atualize o valor fixado e esta tabela em conjunto.

## Deputados eleitos por lista, de 1979 a 1991 (#109)

`ballot_list_elected` tem os 1480 deputados eleitos nas eleições de 1979 (I-B) a 1991 (VI), por círculo e lista, tal como saem nas relações do Diário da República digitalizadas pela CNE. Os nomes são lidos por OCR. Os erros de leitura que se encontraram estão corrigidos em `scripts/cne_elected_fixes.csv`, cada um conferido na digitalização; um nome mal lido que ainda se pareça com um nome real pode ter escapado. Os nomes ficam como o Diário da República os imprime, com as gralhas da época (por exemplo, Octácio por Octávio, em 1991).

- Cada lista tem tantos nomes como lugares em `ballot_list_seats`. `test_every_list_has_the_seats_of_ballot_list_seats` verifica-o.
- `cadastro_id` liga o nome ao registo da AR: pelo nome completo, ou por um nome parecido de um deputado da mesma legislatura, círculo e grupo da lista. Os restantes estão em `models/seeds/ballot_list_elected_overrides.csv`, com uma nota. 18 linhas têm aí o id, muitas vezes porque o registo da AR dá outro círculo, como na I-B, que partilha o registo da I-A (#85).
- Ficam 3 linhas sem `cadastro_id`, porque o apelido impresso não é o do deputado da AR mais provável: Jaime Adalberto Simões Fernandes (1979, Coimbra, AD), Henrique Aureliano Vieira Lopes (1983, Coimbra, PS) e Fernando Ribeiro Martins (1991, Braga, PS). Sem uma segunda fonte não se escolhe.
- Eleito não é o mesmo que ter tido lugar. Quem foi para o governo ou renunciou continua na lista; os mandatos estão em `mandates`.
- 1976 (I-A) fica de fora. A relação de 1976 não traz siglas, as correções vêm num ficheiro à parte, os círculos de então somam 263 lugares, e `ballot_list_seats` não tem linhas da I-A para conferir as contagens. Em 1976 nenhuma coligação elegeu deputados: só PS, PPD, CDS, PCP e UDP elegeram.
