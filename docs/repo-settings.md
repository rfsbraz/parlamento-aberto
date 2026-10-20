# Definições do repositório

Definições de `rfsbraz/parlamento-aberto`, aplicadas por mim na interface do GitHub. Os PR nunca alteram definições; este ficheiro lista-as para serem fáceis de verificar.

| Definição | Valor |
| --- | --- |
| Allow auto-merge | Ligado |
| Automatically delete head branches | Ligado |
| Merge methods | Só squash merge |
| Proteção do branch `main` | Require a pull request before merging |
| Verificações obrigatórias em `main` | `ruff`, `pytest`, `gitleaks`, `file size` |
| Aprovações obrigatórias | Nenhuma, porque os PR de dados são integrados quando as verificações passam |

## Estado (20 de outubro de 2026)

- Só squash merge: ligado.
- Automatically delete head branches: ligado.
- O repositório já é público. Allow auto-merge continua desligado, por isso o workflow dos PR de dados (#3) integra ele próprio os PR de dados limpos quando todas as verificações passam, em vez de depender da integração automática nativa do GitHub.

## Token do bot de dados

Os workflows de dados (`.github/workflows/data-sync.yml`, `data-merge.yml` e `discover.yml`) precisam de um secret do repositório chamado `DATA_BOT_TOKEN`. Sou eu que o crio e guardo em Settings, Secrets and variables, Actions. O valor nunca vai para o git nem para conversas.

Tem de ser um token de instalação de uma GitHub App ou um personal access token fine-grained limitado apenas a `rfsbraz/parlamento-aberto`, com:

| Permissão | Acesso | Usado para |
| --- | --- | --- |
| Contents | Read and write | Fazer push de `data/nightly` e `data/discover`, e fazer squash merge dos PR de dados |
| Pull requests | Read and write | Abrir, atualizar e integrar o PR de dados, e abrir o PR de descoberta em espera |
| Issues | Read and write | Criar e aplicar as etiquetas `data`, `hold:` e `historical-change` |
| Metadata | Read | Exigido pelo GitHub para qualquer token |

O `GITHUB_TOKEN` não o pode substituir: os PR que abre não disparam o CI, e as integrações que faz não disparam os workflows seguintes. Se o secret faltar, o data-sync e o data-merge param no primeiro passo com um erro que indica `DATA_BOT_TOKEN`. O job de descoberta corre na mesma sem ele: não faz push de nada e lista as ligações novas na sua issue, que abre com o `GITHUB_TOKEN`.

Política de integração enquanto a integração automática nativa não está disponível: o `data-merge.yml` corre quando o CI termina no PR `data/nightly` e faz squash merge se o CI passou no head atual do PR e este não tem etiqueta `hold:`. Os PR em espera aguardam que eu os integre.

## Publicações de dados

O `.github/workflows/data-release.yml` corre em cada push para `main` que mexa em `data/`, `src/` ou `docs/data-changelog.md`. Não faz nada quando `main` não tem `data/_meta/sources.lock.json`. Caso contrário, corre todos os testes de dados sobre `data/`, constrói os ficheiros da publicação e compara o número de linhas com a publicação mais recente. Usa apenas o `GITHUB_TOKEN`, com `contents: write` para este job.

A publicação espera pelo meu OK. Enquanto a variável do repositório `DATA_RELEASES` (Settings, Secrets and variables, Actions, Variables) não estiver a `on`, cada execução carrega os ficheiros como artefacto do workflow, guardado durante 7 dias, e não cria publicação nem tag.
