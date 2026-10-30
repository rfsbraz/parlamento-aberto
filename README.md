# parlamento-aberto

Dados abertos sobre a Assembleia da República, limpos, versionados e documentados, reconstruídos a partir dos dumps oficiais de dados abertos. A fonte em bruto fica no git, em `data/`, para que cada alteração feita pela AR apareça como um diff que se pode rever, e cada publicação de dados disponibiliza tabelas em Parquet e CSV construídas a partir dela.

Fonte: Assembleia da República, dados abertos.

A AR permite a reutilização livre dos seus dados abertos, desde que a fonte seja mencionada. Termos: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

## Licenças

- Código: MIT (`LICENSE`).
- Dados: ver `LICENSE-DATA`. Os dados brutos da AR em `data/` são reutilizados nos termos da AR; os marts e o dicionário estão sob CC BY 4.0; os dados da EpT ficam fora da CC BY; os lugares por lista (`ballot_list_seats`) vêm dos ficheiros publicados pela CNE e pela SGMAI, e os deputados eleitos por lista (`ballot_list_elected`) das relações do Diário da República digitalizadas pela CNE, ambos reutilizados ao abrigo da Lei n.º 26/2016, e a CC BY 4.0 cobre só a compilação.

## Dados pessoais

Biografias, datas de nascimento e registos de interesses são dados pessoais. Este repositório republica apenas o que a AR publica.

A AR publica por vezes, em campos de texto livre, números de contribuinte (NIF) e números de beneficiário de cidadãos. O sync substitui-os por `[removido]` (#69), incluindo um NIF escrito em três grupos de três dígitos separados pelo mesmo espaço ou ponto. Os dados dos deputados e das empresas, como um NIPC, ficam como estão. Se algum destes números escapar à máscara, um guard faz falhar o sync antes de escrever. Os commits anteriores mantêm os dados abertos da AR tal como foram publicados: a máscara aplica-se daqui em diante e não reescrevo o histórico.

Para reportar dados errados, abra uma issue com o formulário [Correção de dados](../../issues/new?template=correcao-de-dados.yml). Os pedidos de remoção de dados pessoais podem usar o mesmo formulário, ou o reporte privado de vulnerabilidades do GitHub. Não cole os próprios dados pessoais numa issue pública.

Os números de identificação fiscal não são de acesso público (Lei n.º 52/2019, art. 17.º, n.º 2, al. a); Regulamento da EpT n.º 258/2024, art. 15.º, n.º 2, al. a)). Por isso, de um número de 9 dígitos com dígito de controlo válido, só deixo ficar um NIPC de empresa, com prefixo 5, 6, 71, 72 ou 79. Trato qualquer outro como um NIF pessoal: mascaro-o quando vem depois de uma etiqueta de NIF no texto livre da AR. Isto inclui o prefixo 8 (a antiga gama dos empresários em nome individual), os prefixos 9 (como o 90 e o 91: condomínios, sociedades irregulares e heranças indivisas de empresários em nome individual) e, por precaução, o 77, porque podem identificar uma pessoa. A secção de filiação ou funções em entidades de natureza associativa da EpT fica em `interest_associations`, à parte, e passa pela mesma verificação: só o NIPC de empresa válido fica.

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

Cada push para `main` que altera dados ou código constrói os marts, corre todos os testes de dados sobre `data/` e, se passarem, publica uma GitHub Release com a tag `data-AAAA-MM-DD` (`-2`, `-3` para a segunda ou terceira do dia). Cada publicação tem um ficheiro Parquet e um CSV comprimido com gzip por mart, o `manifest.json` e um excerto `CHANGELOG.md` de `docs/data-changelog.md`. A primeira linha de cada CSV é um comentário `#` com a atribuição, por isso salte uma linha ao ler (`skiprows=1` no pandas, `skip = 1` no R ou no DuckDB). Um mart que perde mais de 5% das linhas numa legislatura, face à publicação anterior, bloqueia a publicação, a menos que `docs/data-changelog.md` o registe. A publicação está desligada até o repositório ser público (ver `docs/repo-settings.md`).

Para construir os mesmos ficheiros localmente:

```sh
uv run python -m parlamento_aberto.release build --data data --out dist --sha "$(git rev-parse HEAD)" --date "$(date +%F)"
```

## Descarregar os dados da AR

```sh
uv run python -m parlamento_aberto fetch                         # legislatura atual
uv run python -m parlamento_aberto fetch --all                   # todas as legislaturas
uv run python -m parlamento_aberto fetch --dataset iniciativas --legislature XVI
uv run python -m parlamento_aberto fetch --dataset intervencoes --legislature XVII --prune
```

O `sources.yaml` lista todos os ficheiros. A legislatura mais recente que lá consta é a atual. Os pedidos são feitos um de cada vez, com gzip, e as páginas temporárias "Recurso Não Encontrado" da AR são repetidas com espera crescente. Corra depois das 06:00, hora de Lisboa; o servidor da AR é lento entre as 04:00 e as 06:00. Os ficheiros cujo hash coincide com `data/_meta/sources.lock.json` são saltados. Um ficheiro descarregado que seja HTML, não se consiga ler, venha vazio quando a última cópia tinha registos, ou tenha mais de 5% menos registos do que ela mantém a última cópia boa e fica marcado como desatualizado (stale) no lock, com o motivo (por exemplo `row drop 7984 to 81`). Só as fontes com `rolling: true` no `sources.yaml`, como a agenda, que só lista as próximas semanas, escrevem essa queda e a assinalam (#135). As fontes com `merge: upsert`, descritas abaixo, medem a queda no total guardado depois da junção e assinalam-na. `--raw-dir DIR` guarda os ficheiros descarregados fora do repositório, e `--offline` volta a usá-los. As intervenções e as iniciativas têm `merge: upsert` no `sources.yaml`, porque a AR por vezes publica só uma parte do ficheiro (81 intervenções da XVII em vez de 7984): os registos do ficheiro atualizam e acrescentam por id, os que ficam de fora mantêm-se e as linhas sem id são descartadas. O lock guarda o total guardado em `records` e o total do ficheiro da AR em `source_records`, e o relatório mostra quantos registos guardados faltam no ficheiro. Só `--prune` apaga os registos que a AR deixou de publicar; corre-se à mão e o resultado vai num PR revisto (#133).

## Registo de interesses da EpT

Os elementos públicos do registo de interesses dos Deputados da XVI e da XVII são republicados com indicação da Entidade para a Transparência (EpT) como fonte, ao abrigo da Lei n.º 52/2019, art. 15.º, n.º 1, e da Lei n.º 26/2016 (LADA), art. 21.º, n.º 1. Ficam excluídos o NIF dos titulares, os dados pessoais, os rendimentos e património, as filiações associativas e os anexos. As regras estão em `LICENSE-DATA` (ponto 3) e em `docs/sources/ept.md`.

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
