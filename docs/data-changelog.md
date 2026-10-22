# Changelog dos dados

Alterações aos marts publicados que quem usa os dados deve conhecer. A secção `## Unreleased` vai para a próxima publicação como o seu `CHANGELOG.md`.

- Alterações ao schema: uma linha cada, por exemplo `- schema: votes gains committee_id.` Suba também `schema_version` em `src/parlamento_aberto/models/schema.yml`, a versão major numa alteração incompatível.
- Quedas de linhas: um mart que perde mais de 5% das linhas numa legislatura, face à publicação anterior, bloqueia a publicação. Se a queda estiver correta, registe-a com `- drift: <mart> <legislature>: motivo`, usando `all` para marts sem coluna de legislatura. Uma linha que a publicação anterior já trazia não volta a contar.

Depois de uma publicação, passe as linhas publicadas para um título com a respetiva tag.

Os títulos `## Unreleased` e os prefixos `schema:` e `drift:` ficam em inglês, porque o build de publicação os lê.

## Unreleased

- schema: primeira publicação, schema 1.0.0.
- schema: interest_declarations ganha source, source_format, source_declaration_id, ept_holder_id, declaration_nature, declaration_state, supersedes_declaration_id, superseded_by_declaration_id, chain_root_declaration_id, submitted_at, submitted_date e is_current, no fim (schema 1.1.0).
- schema: interests ganha source, paid_raw, entity_nipc, beneficiary, beneficiary_company, share_value_eur, share_pct, share_holder, is_professional_secrecy e observation, no fim.
- schema: manifest.json ganha excluded_sources. As linhas com source = ept ficam fora dos ficheiros publicados, por não estarem cobertas pela CC BY 4.0.
- schema: novos marts plenary_attendance e plenary_attendance_summary, com as presenças e faltas às reuniões plenárias da V à XVII por reunião, a categoria de cada código e a marca das reuniões solenes e comemorativas, sem o motivo da falta (schema 1.2.0).
- schema: novo mart ballot_list_seats, com os lugares por lista e círculo eleitoral de 2009 (XI) a 2025 (XVII), tal como publicados pela SGMAI. manifest.json ganha attribution e downloaded (data de descarga) por mart, e source_files com a data de cada ficheiro da SGMAI quando o ficheiro a indica (schema 1.3.0).
