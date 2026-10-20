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
| [interest_declarations](interest_declarations.md) | Uma linha por declaração no registo de interesses, XI a XV. |
| [interests](interests.md) | Uma linha por interesse declarado: atividades e cargos, cargos sociais, sociedades, apoios, serviços e outras situações. |

## Licença e atribuição

Os dados são publicados sob CC BY 4.0 (`LICENSE-DATA`). A AR permite a reutilização
livre dos seus dados abertos, desde que a fonte seja mencionada. Indique-a assim:

> Fonte: Assembleia da República, dados abertos.

Termos: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

Todos os CSV de uma publicação começam com essa linha, que também consta do
`manifest.json`.

As linhas de `interest_declarations` e `interests` com `source = 'ept'` vêm da
Entidade para a Transparência (XVI e XVII) e não estão cobertas pela CC BY 4.0: a EpT
não deu autorização de reutilização (Lei n.º 52/2019, art. 17.º). Ficam fora dos
ficheiros publicados, e o `manifest.json` conta-as em `excluded_sources`. Ver
[sources/ept.md](../sources/ept.md).

Biografias, datas de nascimento e registos de interesses são dados pessoais. Os marts
contêm apenas o que a AR e a EpT publicam, sem os campos que deixamos de fora. Para
reportar dados errados, veja o README principal.
