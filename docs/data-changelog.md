# Changelog dos dados

Alterações aos marts publicados que quem usa os dados deve conhecer. A secção `## Unreleased` vai para a próxima publicação como o seu `CHANGELOG.md`.

- Alterações ao schema: uma linha cada, por exemplo `- schema: votes gains committee_id.` Suba também `schema_version` em `src/parlamento_aberto/models/schema.yml`, a versão major numa alteração incompatível.
- Quedas de linhas: um mart que perde mais de 5% das linhas numa legislatura, face à publicação anterior, bloqueia a publicação. Se a queda estiver correta, registe-a com `- drift: <mart> <legislature>: motivo`, usando `all` para marts sem coluna de legislatura. Uma linha que a publicação anterior já trazia não volta a contar.

Depois de uma publicação, passe as linhas publicadas para um título com a respetiva tag.

Os títulos `## Unreleased` e os prefixos `schema:` e `drift:` ficam em inglês, porque o build de publicação os lê.

## Unreleased

- schema: primeira publicação, schema 1.0.0.
