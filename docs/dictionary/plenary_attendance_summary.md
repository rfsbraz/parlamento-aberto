# plenary_attendance_summary

Uma linha por legislatura, pessoa, grupo e tipo de reunião (solene ou comemorativa, ou não), a partir de plenary_attendance: o número de reuniões nas listas de presenças e quantas caem em cada categoria, para que qualquer taxa se possa calcular. Cada reunião conta uma vez, mesmo em dias com mais do que uma. Para deixar de fora as reuniões solenes e comemorativas, filtre is_ceremonial = false; para as incluir, some as duas linhas. Quem mudou de grupo na legislatura tem linhas por grupo. Mostre sempre meetings ao lado de uma taxa: muitos substitutos têm poucas reuniões.

Gerado a partir de `src/parlamento_aberto/models/schema.yml` por `uv run python -m parlamento_aberto.dictionary`. Não editar à mão.

Ficheiros da publicação: `plenary_attendance_summary.parquet` e `plenary_attendance_summary.csv.gz`.

## Colunas

| Coluna | Tipo | Descrição |
|---|---|---|
| `legislature` | VARCHAR | Legislatura em numeração romana. |
| `cadastro_id` | BIGINT | Id da pessoa, liga a deputies. |
| `parliamentary_name` | VARCHAR | Nome parlamentar na reunião mais recente. |
| `group_code` | VARCHAR | Código do grupo depois de seed_group_aliases. |
| `is_ceremonial` | BOOLEAN | Verdadeiro na linha das reuniões solenes e comemorativas. |
| `meetings` | INTEGER | Número de reuniões plenárias em cujas listas de presenças a pessoa consta com este grupo. |
| `present` | INTEGER | Reuniões com presença (PT, PR e PP). |
| `other_body_or_mission` | INTEGER | Reuniões noutro órgão, em comissão autorizada pelo Presidente da AR ou em missão parlamentar (PNO, CO, ME e MP). |
| `justified` | INTEGER | Faltas justificadas (FJ, FIJ, FAJ e QVJ). |
| `missed_quorum_vote` | INTEGER | Faltas ao quórum de votação (QV). |
| `pending` | INTEGER | Faltas FA por justificar, com menos de 60 dias em source_updated. |
| `unclassified` | INTEGER | Faltas FA não classificadas, com 60 dias ou mais em source_updated. |
| `unjustified` | INTEGER | Faltas injustificadas (FI). |
| `first_meeting_date` | DATE | Data da primeira dessas reuniões. |
| `last_meeting_date` | DATE | Data da última dessas reuniões. |

## Particularidades conhecidas

- As lacunas da própria fonte da AR estão em [lacunas conhecidas](../known-gaps.md).

## Construído a partir de

Marts: [plenary_attendance](plenary_attendance.md).
