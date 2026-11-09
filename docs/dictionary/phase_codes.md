# phase_codes

Uma linha por código de fase dos eventos das iniciativas, com a categoria de desfecho que a fase indica. É seed_phase_codes tal como mantido à mão, publicado para se poder juntar a initiative_events.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `phase_codes.parquet` e `phase_codes.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `phase_code` | VARCHAR | Código da fase (CodigoFase), liga a initiative_events. |
| `phase` | VARCHAR | Nome da fase tal como publicado, sem espaços nem quebras de linha no fim. |
| `outcome` | VARCHAR | Desfecho que a fase indica, com as categorias descritas em seed_phase_codes. |
| `note` | VARCHAR | Nota sobre a fase, vazia quando o nome basta. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [initiative_events](initiative_events.md).

### seed_phase_codes

Códigos de fase dos eventos das iniciativas (CodigoFase), mantidos à mão, uma linha por código, com a categoria de desfecho que a fase indica. Um código que apareça nos eventos e não esteja aqui faz falhar os testes de dados, até ter a sua linha.

| Coluna | Tipo | Descrição |
|---|---|---|
| `phase_code` | VARCHAR | Código da fase (CodigoFase), por exemplo 580. |
| `phase` | VARCHAR | Nome da fase tal como publicado, sem espaços nem quebras de linha no fim. |
| `outcome` | VARCHAR | Desfecho que a fase indica: in_progress (a fase não fecha a iniciativa), approved_published (lei, resolução ou regimento publicado no Diário da República, ou deliberação publicada no Diário da Assembleia da República), rejected (não admitida), lapsed (caducada), withdrawn (retirada), prejudiced (prejudicada) ou vetoed (vetada, o decreto pode ainda ser confirmado ou reapreciado). As votações ficam em in_progress, porque o resultado está em votes. |
| `note` | VARCHAR | Nota sobre a fase, vazia quando o nome basta. |
