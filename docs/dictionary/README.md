# Dicionário de dados

Uma página por mart da publicação de dados, com os tipos e as descrições das colunas,
as particularidades conhecidas e os modelos de staging a partir dos quais cada mart é
construído. As descrições das colunas de staging indicam entre parênteses o campo da
fonte da AR, por exemplo `(dtini)`.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Como consultar uma publicação: [querying.md](../querying.md).

## Marts

| Mart | Descrição |
|---|---|
| [legislatures](legislatures.md) | Uma linha por legislatura. |
| [sessions](sessions.md) | Uma linha por sessão legislativa. |
| [electoral_circles](electoral_circles.md) | Uma linha por círculo eleitoral e por legislatura. |
| [parliamentary_groups](parliamentary_groups.md) | Uma linha por grupo parlamentar e por legislatura. |
| [coalitions](coalitions.md) | Uma linha por legislatura, lista da coligação e grupo parlamentar, a partir de seed_coalitions. |
| [ballot_list_seats](ballot_list_seats.md) | Uma linha por eleição, círculo eleitoral e lista que ganhou pelo menos um lugar, com os lugares tal como publicados pela CNE, de 1979 (I-B) a 2005 (X), e pela SGMAI, de 2009 (XI) a 2025 (XVII). |
| [ballot_list_elected](ballot_list_elected.md) | Uma linha por deputado eleito, por eleição, círculo eleitoral e lista, de 1979 (I-B) a 1991 (VI), com o nome tal como publicado no Diário da República e o cadastro_id da AR. |
| [deputies](deputies.md) | Uma linha por pessoa (cadastro_id) que aparece em qualquer lista, eleita ou não. |
| [mandates](mandates.md) | Uma linha por deputado, legislatura e período de situação (DepSituacao), tal como publicado. |
| [group_memberships](group_memberships.md) | Uma linha por deputado, legislatura e período num grupo parlamentar (DepGP). |
| [initiatives](initiatives.md) | Uma linha por iniciativa. |
| [initiative_authors](initiative_authors.md) | Uma linha por autor de uma iniciativa. |
| [votes](votes.md) | Uma linha por id de votação, a partir dos arrays Votacao dos eventos das Iniciativas (plenário), das suas entradas Comissao (comissão) e dos arrays VotacaoDebate das Atividades (plenário). |
| [initiative_votes](initiative_votes.md) | Liga as votações em plenário e em comissão às iniciativas e eventos em que são publicadas. |
| [vote_group_positions](vote_group_positions.md) | Uma linha por votação, grupo e sentido de voto, a partir do detalhe lido. |
| [vote_deputy_dissents](vote_deputy_dissents.md) | Uma linha por deputado nomeado no detalhe de uma votação, normalmente por votar de forma diferente do seu grupo, ou nomeado como ausente no campo ausencias de uma votação sem detalhe. |
| [interventions](interventions.md) | Uma linha por intervenção em plenário, com debate, orador e referência no Diário. |
| [questions](questions.md) | Uma linha por pergunta ou requerimento que um deputado enviou ao Governo ou a outro organismo público. |
| [question_authors](question_authors.md) | Uma linha por pergunta e autor. |
| [question_recipients](question_recipients.md) | Uma linha por pergunta e organismo destinatário. |
| [interest_declarations](interest_declarations.md) | Uma linha por declaração no registo de interesses, de duas fontes: os dados abertos da AR (source = ar_open_data, XI a XV) e a Entidade para a Transparência (source = ept, XVI e XVII). |
| [interests](interests.md) | Uma linha por interesse declarado, das mesmas duas fontes de interest_declarations (ar_open_data, XI a XV, e ept, XVI e XVII): atividades e cargos, cargos sociais, sociedades, apoios, serviços e outras situações. |
| [plenary_attendance](plenary_attendance.md) | Uma linha por reunião plenária e pessoa na sua lista de presenças. |
| [plenary_attendance_summary](plenary_attendance_summary.md) | Uma linha por legislatura, pessoa, grupo e tipo de reunião (solene ou comemorativa, ou não), a partir de plenary_attendance: o número de reuniões nas listas de presenças e quantas caem em cada categoria, para que qualquer taxa se possa calcular. |

## Licença e atribuição

Os marts publicados e este dicionário estão sob CC BY 4.0
(`LICENSE-DATA`), com a Assembleia da República como fonte. Cite assim, com a data de
atualização que vem no `manifest.json` (`source_updated`):

> Fonte: Assembleia da República, dados abertos, atualizados a AAAA-MM-DD.

Dados brutos em `data/`. Dados abertos da Assembleia da República reutilizados nos termos da AR, com a fonte e a data de atualização (Lei n.º 26/2016, art. 19.º, n.º 5).
Termos da AR: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

`data/ept_*` e tudo o que deriva deles. Registo de interesses da XVI e da XVII: Fonte: Entidade para a Transparência (EpT), republicado ao abrigo da Lei n.º 52/2019, art. 15.º, n.º 1, e da Lei n.º 26/2016 (LADA), art. 21.º, n.º 1, fora da licença dos marts. Ficam excluídos o NIF dos titulares, os dados pessoais, os rendimentos e património, as filiações associativas e os anexos.

Cada CSV de uma publicação começa com a fonte, a data de atualização e a licença do mart,
e o `manifest.json` traz o mesmo por mart.

As linhas de `interest_declarations` e `interests` com `source = 'ept'` vêm da
Entidade para a Transparência (XVI e XVII) e não estão cobertas pela CC BY 4.0
(`LICENSE-DATA`, ponto 3). Entram nos ficheiros publicados com os termos da EpT no
cabeçalho do CSV e no `manifest.json`, depois de a publicação confirmar que nenhuma
tem um número fiscal. Ver
[sources/ept.md](../sources/ept.md).

`ballot_list_seats` vem dos mapas de resultados publicados pela Comissão Nacional de
Eleições (CNE), de 1979 a 2005, e dos ficheiros de resultados eleitorais publicados pela
Secretaria-Geral do Ministério da Administração Interna (SGMAI), de 2009 a 2025, não da
AR, reutilizados ao abrigo dos artigos 19.º e 21.º da Lei n.º 26/2016. A CC BY 4.0
aplica-se à compilação feita por este projeto e não implica qualquer aprovação da CNE ou
da SGMAI (`LICENSE-DATA`, ponto 4). O CSV e o `manifest.json` desse mart citam as
duas fontes com a data de descarga (`downloaded`), e o `manifest.json` traz, por
ficheiro, quem o publica (`publisher`) e a data do ficheiro quando este a indica
(`source_files`):

> Fonte: CNE (1979 a 2005) e SGMAI (2009 a 2025), resultados das eleições para a Assembleia da República, descarregados a AAAA-MM-DD

Biografias, datas de nascimento e registos de interesses são dados pessoais. Os marts
contêm apenas o que a AR e a EpT publicam, sem os campos que deixamos de fora. Para
reportar dados errados, veja o README principal.
