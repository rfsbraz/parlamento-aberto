# Como contribuir

Obrigado pelo interesse no parlamento-aberto. Este repositório reconstrói, a partir dos dados abertos oficiais, dados limpos, versionados e documentados sobre a Assembleia da República. Este guia explica como preparar o ambiente, que verificações correr antes de abrir um pull request e que regras seguir com dados pessoais.

## Antes de começar

- Para reportar um dado errado, ou pedir a correção ou remoção de dados pessoais, abra uma issue com o formulário [Correção de dados](https://github.com/rfsbraz/parlamento-aberto/issues/new?template=correcao-de-dados.yml). Não escreva os dados pessoais na issue: indique só onde está o problema.
- Para reportar uma vulnerabilidade ou uma fuga de dados que não deviam estar publicados, siga o [SECURITY.md](SECURITY.md) e não abra uma issue pública.
- Para uma alteração maior (um modelo novo, uma fonte nova, uma mudança no esquema), abra primeiro uma issue a descrever a ideia.

## Preparar o ambiente

É preciso Python 3.12 e o [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/rfsbraz/parlamento-aberto.git
cd parlamento-aberto
uv sync
```

O histórico inclui os dados brutos em `data/` e ocupa vários GB. Se só precisa do código, um clone parcial (`git clone --filter=blob:none`) é mais rápido.

Os testes não usam a rede. Os comandos de recolha (`python -m parlamento_aberto fetch` e `python -m parlamento_aberto.ept`) fazem pedidos aos servidores da AR e da Entidade para a Transparência: não os corra em ciclo e respeite os intervalos descritos no README.

## Verificações antes de um pull request

A CI corre estas verificações em cada pull request. Corra-as localmente antes de enviar:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run python -m parlamento_aberto.dictionary --check
uv run python scripts/check_file_size.py
gitleaks git --redact --verbose --exit-code 1 --log-opts="origin/main..HEAD" .
```

- `ruff` verifica o estilo e a formatação (`uv run ruff format .` corrige a formatação).
- `pytest` corre todos os testes, incluindo os testes de dados sobre as fixtures.
- `dictionary --check` falha se `docs/dictionary` não corresponder a `src/parlamento_aberto/models/schema.yml`. O dicionário é gerado: não edite essas páginas à mão. Altere as descrições no `schema.yml` e gere de novo com `uv run python -m parlamento_aberto.dictionary`.
- `check_file_size.py` rejeita qualquer ficheiro acima de 50 MB.
- O [gitleaks](https://github.com/gitleaks/gitleaks) procura segredos nos commits do seu ramo, com as regras de `.gitleaks.toml`. Essas regras incluem duas para os dados da Entidade para a Transparência, que falham com qualquer NIF ou valor de 9 dígitos fora da coluna de NIPC. Não altere nem contorne estas regras para fazer passar um commit.

## Dados pessoais e fixtures

Os dados de deputados incluem dados pessoais. As regras abaixo não têm exceções:

- Nunca escreva um NIF pessoal, nem o NIF do titular de uma declaração, em código, fixtures, logs, issues ou commits. Dos dados da Entidade para a Transparência só se guardam os metadados da declaração e o separador 4 (registo de interesses). Os separadores 2 (dados pessoais) e 3 (rendimentos e património) nunca entram no repositório.
- Na coluna NIF/NIPC do separador 4 só fica um NIPC de empresa válido. As regras estão em [docs/sources/ept.md](docs/sources/ept.md).
- As fixtures são sintéticas ou depuradas. Nomes e texto livre inventados usam `Pessoa Sintética`, `sintético` ou `sintética`, e as ligações apontam para `https://app.parlamento.pt/fixture/`. Os testes verificam isto, e falham se uma fixture da EpT tiver uma chave `nif` ou um valor de 9 dígitos.
- Cada fixture nova é descrita em [tests/fixtures/README.md](tests/fixtures/README.md): de onde vem, a data da extração e o que foi inventado ou retirado.
- Não edite `data/` à mão. Esses ficheiros vêm da sincronização automática com os dados abertos da AR. Um dado errado na fonte reporta-se com o formulário de correção.

## Commits e pull requests

- Abra cada pull request a partir de `main`, com uma alteração por pull request.
- Use [Conventional Commits](https://www.conventionalcommits.org/), com o prefixo em inglês e o texto em português de Portugal, por exemplo `docs: traduz README` ou `fix(marts): não conta deputados duas vezes em dias de substituição`.
- O título do pull request segue a mesma forma, porque é ele que fica no histórico quando o pull request é integrado (squash merge).
- Escreva o título, a descrição, as issues e os comentários em português de Portugal. Código, identificadores, nomes de colunas e mensagens da linha de comandos ficam em inglês.
- Preencha o modelo de pull request: o que muda, porquê, que issue fecha e como foi testado.
- Para atualizar um ramo, faça merge de `main` no ramo.

## Licenças

Ao contribuir, aceita que o código que enviar fica sob a licença MIT ([LICENSE](LICENSE)) e que os dados ficam sob os termos de [LICENSE-DATA](LICENSE-DATA).
