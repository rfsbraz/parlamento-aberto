# parlamento-aberto

Dados abertos sobre a Assembleia da República, limpos, versionados e documentados, reconstruídos a partir dos dumps oficiais de dados abertos. A fonte em bruto fica no git, em `data/`, para que cada alteração feita pela AR apareça como um diff que se pode rever, e cada publicação de dados disponibiliza tabelas em Parquet e CSV construídas a partir dela.

Fonte: Assembleia da República, dados abertos.

A AR permite a reutilização livre dos seus dados abertos, desde que a fonte seja mencionada. Termos: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

## Licenças

- Código: MIT (`LICENSE`).
- Dados: ver `LICENSE-DATA`. Os dados brutos da AR em `data/` são reutilizados nos termos da AR; os marts e o dicionário estão sob CC BY 4.0; os dados da EpT ficam fora da CC BY.

## Dados pessoais

Biografias, datas de nascimento e registos de interesses são dados pessoais. Este repositório republica apenas o que a AR publica.

A AR publica por vezes, em campos de texto livre, números de contribuinte (NIF) e números de beneficiário de cidadãos. O sync substitui-os por `[removido]` (#69), incluindo um NIF escrito em três grupos de três dígitos separados pelo mesmo espaço ou ponto. Os dados dos deputados e das empresas, como um NIPC, ficam como estão. Se algum destes números escapar à máscara, um guard faz falhar o sync antes de escrever. Os commits anteriores mantêm os dados abertos da AR tal como foram publicados: a máscara aplica-se daqui em diante e não reescrevo o histórico.

Para reportar dados errados, abra uma issue com o formulário [Correção de dados](../../issues/new?template=correcao-de-dados.yml). Os pedidos de remoção de dados pessoais podem usar o mesmo formulário, ou o reporte privado de vulnerabilidades do GitHub. Não cole os próprios dados pessoais numa issue pública.

Os números de identificação fiscal não são de acesso público (Lei n.º 52/2019, art. 17.º, n.º 2, al. a); Regulamento da EpT n.º 258/2024, art. 15.º, n.º 2, al. a)). Por isso, de um número de 9 dígitos com dígito de controlo válido, só deixo ficar um NIPC de empresa, com prefixo 5, 6, 71, 72 ou 79. Trato qualquer outro como um NIF pessoal: mascaro-o quando vem depois de uma etiqueta de NIF no texto livre da AR e descarto-o na coluna NIF/NIPC da EpT. Isto inclui o prefixo 8 (a antiga gama dos empresários em nome individual), os prefixos 9 (como o 90 e o 91: condomínios, sociedades irregulares e heranças indivisas de empresários em nome individual) e, por precaução, o 77, porque podem identificar uma pessoa. Da EpT também não guardo a secção de filiação ou funções em entidades de natureza associativa, que fica fora do acesso público (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)).

## Desenvolvimento

Requer o [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python scripts/check_file_size.py
```

## Publicações de dados

Cada push para `main` que altera dados ou código constrói os marts, corre todos os testes de dados sobre `data/` e, se passarem, publica uma GitHub Release com a tag `data-AAAA-MM-DD` (`-2`, `-3` para a segunda ou terceira do dia). Cada publicação tem um ficheiro Parquet e um CSV comprimido com gzip por mart, o `macros.sql` com a regra de quem tem lugar num dia, o `manifest.json` e um excerto `CHANGELOG.md` de `docs/data-changelog.md`. A primeira linha de cada CSV é um comentário `#` com a atribuição, por isso salte uma linha ao ler (`skiprows=1` no pandas, `skip = 1` no R ou no DuckDB). Um mart que perde mais de 5% das linhas numa legislatura, face à publicação anterior, bloqueia a publicação, a menos que `docs/data-changelog.md` o registe. A publicação está desligada até o repositório ser público (ver `docs/repo-settings.md`).

Para construir os mesmos ficheiros localmente:

```sh
uv run python -m parlamento_aberto.release build --data data --out dist --sha "$(git rev-parse HEAD)" --date "$(date +%F)"
```

## Descarregar os dados da AR

```sh
uv run python -m parlamento_aberto fetch                         # legislatura atual
uv run python -m parlamento_aberto fetch --all                   # todas as legislaturas
uv run python -m parlamento_aberto fetch --dataset iniciativas --legislature XVI
```

O `sources.yaml` lista todos os ficheiros. A legislatura mais recente que lá consta é a atual. Os pedidos são feitos um de cada vez, com gzip, e as páginas temporárias "Recurso Não Encontrado" da AR são repetidas com espera crescente. Corra depois das 06:00, hora de Lisboa; o servidor da AR é lento entre as 04:00 e as 06:00. Os ficheiros cujo hash coincide com `data/_meta/sources.lock.json` são saltados. Um ficheiro descarregado que seja HTML, não se consiga ler, ou venha vazio quando a última cópia tinha registos mantém a última cópia boa e fica marcado como desatualizado (stale) no lock. `--raw-dir DIR` guarda os ficheiros descarregados fora do repositório, e `--offline` volta a usá-los.

## Descarregar o registo de interesses da EpT

Os dados abertos da AR só têm o registo de interesses até à XV. As declarações da XVI e da XVII estão na Entidade para a Transparência (EpT), que tem uma API JSON pública (#42). O código é público, mas os dados da EpT só são republicados depois de a EpT responder ao meu pedido de reutilização (ver `docs/sources/ept.md`).

```sh
uv run python -m parlamento_aberto.ept dry-run            # só contagens, não escreve nada
uv run python -m parlamento_aberto.ept fetch              # para data/ept_registo_interesses
uv run python -m parlamento_aberto.ept fetch --limit 5    # os primeiros 5 titulares, para uma verificação rápida
```

Lê as entidades 510 (Assembleia da República) e 4508 (Assembleia da República - XVII Legislatura) da EpT: as titularidades, depois as declarações de cada titular em todos os estados, depois cada declaração nova ou alterada. Os pedidos são feitos um de cada vez, no máximo um por segundo. A 20 de outubro de 2026 eram 881 titularidades, 695 pesquisas de titulares e 1424 declarações, pelo que uma primeira execução completa demora cerca de uma hora. Uma declaração só volta a ser descarregada quando o seu estado muda, e as versões substituídas ou modificadas ficam guardadas com os seus próprios ids.

Cada declaração é limpa em memória antes de se escrever o que quer que seja. Só ficam os metadados (ids, entidade, cargo, titular, natureza, estado, declaração relacionada, datas) e o separador 4 (atividades, apoios, serviços, sociedades, outras situações). A secção de filiação ou funções em entidades de natureza associativa é descartada inteira, sem ler nenhuma célula (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)). O NIF do titular, os dados pessoais, os rendimentos e património e os anexos são descartados, e qualquer número de 9 dígitos que reste num valor passa a `[removido]`.

A coluna NIF/NIPC da entidade no separador 4 só mantém um NIPC de empresa válido: 9 dígitos (depois de retirar espaços, pontos, hífenes e um prefixo `PT`), um dígito de controlo mod 11 válido e um primeiro dígito 5 ou 6 ou um prefixo 71, 72 ou 79. Tudo o resto nessa coluna é descartado: primeiro dígito de 1 a 4 (pessoas singulares), 8 (antigos empresários em nome individual), 9 (condomínios, sociedades irregulares, heranças indivisas), 0, qualquer outro prefixo 7x (incluindo o 77), um dígito de controlo errado, ou texto (Lei n.º 52/2019, art. 17.º, n.º 2, al. a); Regulamento da EpT n.º 258/2024, art. 15.º, n.º 2, al. a)).

Um ficheiro com uma chave `nif`, a secção de associações, um valor fora dos prefixos de empresa, ou um valor de 9 dígitos fora da coluna NIPC nunca é escrito: em vez disso, a execução para. Duas regras do gitleaks em `.gitleaks.toml` verificam o mesmo em `data/ept_registo_interesses/` e `tests/fixtures/ept/` (o dígito de controlo fica a cargo dos testes). Os logs e o relatório da execução só contêm contagens e ids.

Estrutura: `data/ept_registo_interesses/titularidades.ndjson`, `declarations.ndjson` (os resultados da pesquisa, por id) e `<id da entidade>/<id // 1000>/<id>.json` (uma declaração limpa, com o separador 4 indexado por GUID da secção e coluna).

O build lê as declarações guardadas para `stg_ept_registo_interesses__declarations` e `stg_ept_registo_interesses__items` (#46), com as mesmas primeiras colunas das tabelas de staging da XI à XV. Só são lidas as declarações de Deputado e Deputada. A legislatura vem do dia, em Lisboa, do início do cargo (ou da entrega, quando não há início), não do órgão da EpT, por isso as linhas da entidade 510 caem na XIV, XV ou XVI. As datas em UTC passam a dias de Lisboa e os valores publicados ficam nas colunas `_raw`. As versões substituídas e modificadas ficam como linhas, ligadas por `supersedes_declaration_id`, `superseded_by_declaration_id` e `chain_root_declaration_id`, e `is_current` marca a mais recente publicada sem sucessora. A coluna NIPC passa para `entity_nipc`, só com NIPC de empresas válidos.

## Dicionário de dados

`docs/dictionary` tem uma página por mart, gerada a partir de `src/parlamento_aberto/models/schema.yml`. `docs/querying.md` mostra como consultar uma publicação com DuckDB, pandas e R. Depois de alterar um modelo ou as descrições das suas colunas, volte a gerar as páginas; o CI falha quando estão desatualizadas:

```sh
uv run python -m parlamento_aberto.dictionary
```

## Descoberta

Todas as segundas-feiras às 08:00, hora de Lisboa, `.github/workflows/discover.yml` lê as páginas de dados abertos da AR e compara as suas ligações JSON com o `sources.yaml`. As ligações novas de um conjunto de dados conhecido, como uma nova legislatura, dão origem a um PR em `data/discover` com a etiqueta `hold: new-dataset`, que nunca é integrado automaticamente. As ligações removidas, os ficheiros que não correspondem a nenhum conjunto de dados e as páginas que não consegue ler dão origem a uma issue com a etiqueta `discover`. O bloco `discover` do `sources.yaml` lista o que fica de fora de propósito. Para correr localmente (cerca de 300 pedidos, com dois segundos de intervalo):

```sh
uv run python -m parlamento_aberto.discover scan --scan scan.json
uv run python -m parlamento_aberto.discover diff --scan scan.json --report report.json
```

Desenho: `docs/design.md`. Definições do repositório: `docs/repo-settings.md`.
