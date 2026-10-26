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
- schema: coalitions ganha has_seats, no fim, e uma linha por cada partido da lista que não elegeu ninguém, com has_seats falso: o PEV na CDU da XV à XVII e o PPM na AD da XVI e na lista da AD dos Açores na XVII (schema 1.3.0).
- coalitions ganha as listas regionais que faltavam: PPD/PSD.CDS-PP (Madeira Primeiro) na Madeira, na XV e na XVI, e PPD/PSD.CDS-PP.PPM (AD/Aliança Democrática) nos Açores, na XV. Os deputados destas listas sentaram-se no PSD (#92).
- drift: mandates I-A: a AR publica a mesma lista para a I-A e a I-B; cada parte fica só com os períodos que se sobrepõem às suas datas (#85).
- drift: mandates I-B: a AR publica a mesma lista para a I-A e a I-B; cada parte fica só com os períodos que se sobrepõem às suas datas (#85).
- drift: group_memberships I-A: a AR publica a mesma lista para a I-A e a I-B; cada parte fica só com os períodos que se sobrepõem às suas datas (#85).
- drift: group_memberships I-B: a AR publica a mesma lista para a I-A e a I-B; cada parte fica só com os períodos que se sobrepõem às suas datas (#85).
- schema: novo mart ballot_list_seats, com os lugares por lista e círculo eleitoral de 2009 (XI) a 2025 (XVII), tal como publicados pela SGMAI. manifest.json ganha attribution e downloaded (data de descarga) por mart, e source_files com a data de cada ficheiro da SGMAI quando o ficheiro a indica (schema 1.4.0).
- schema: ballot_list_seats passa a cobrir 1979 (I-B) a 2005 (X), com os lugares por lista e círculo dos mapas de resultados da CNE, com as siglas na grafia da SGMAI e uma correção em 1983 (Fora da Europa) segundo o Diário da República. Cada ficheiro em source_files do manifest.json ganha publisher (CNE ou SGMAI), e a fonte do mart passa a citar a CNE e a SGMAI (schema 1.5.0, #107).
- schema: novo mart ballot_list_elected, com os deputados eleitos por círculo e lista nas eleições de 1979 (I-B) a 1991 (VI), segundo as relações do Diário da República digitalizadas pela CNE, e o cadastro_id da AR de cada um quando se encontra (schema 1.6.0, #109).
- coalitions: o CDS-PP passa a ter has_seats falso, e group_name nulo, nas listas PPD/PSD.CDS-PP da Madeira na XVI e PPD/PSD.CDS-PP.PPM dos Açores na XVII, que só elegeram deputados do PSD. has_seats passa a ler-se por lista (#119).
