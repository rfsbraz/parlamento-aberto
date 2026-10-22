# Entidade para a Transparência (EpT): registo de interesses da XVI e da XVII

Os dados abertos da AR só têm ficheiros `RegistoInteresses` até à XV. A partir da XVI, os deputados entregam as declarações à Entidade para a Transparência, ao abrigo da Lei n.º 52/2019, e a AR não publica nenhuma. Esta página regista o que decidi, o que a API da EpT devolve e o que nunca guardo. Plano e ordem de construção: #42 (issues #43 a #49).

## Decisão (20 de outubro de 2026)

- O código é público, como o resto do repositório. As declarações da XVI e da XVII são normalizadas nos mesmos marts `interest_declarations` e `interests` da XI à XV, com `source = 'ept'`.
- Sem republicação por agora. As linhas da EpT não entram numa publicação de dados, no site nem no repositório até a EpT responder ao meu pedido e eu decidir com base na resposta.
- Sem contacto com a EpT para além de um email a perguntar se os dados podem ser reutilizados. Não envio mais nada enquanto não houver resposta.
- Não guardo a secção de filiação ou funções em entidades de natureza associativa (decidido a 20 de outubro de 2026). Fica fora do acesso público (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)), por isso descarto-a inteira, sem ler nenhuma célula.
- O PR de dados `ept_registo_interesses` fica em espera (novo conjunto de dados, etiqueta `hold:`), nunca é integrado automaticamente e sou eu que decido quando o integrar.
- **Republicação: pendente da resposta da EpT.** A questão legal abaixo tem de estar resolvida antes de quaisquer dados derivados da EpT serem publicados.

## Limites legais: Lei n.º 52/2019, art. 17.º

Texto consolidado após a Lei n.º 58/2021 e a Lei n.º 4/2022 ([pgdlisboa.pt](https://pgdlisboa.pt/leis/lei_mostra_articulado.php?nid=3192&tabela=leis)).

- n.º 1: as declarações são de acesso público, nos termos do artigo.
- n.º 2: nunca são públicos: (a) morada, números de identificação civil e fiscal, números de telefone e email; (b) no registo de interesses, o detalhe dos serviços prestados ao abrigo de segredo profissional; (c) dados que identifiquem a residência (para além do concelho) ou veículos.
- n.º 3 e n.º 5: os rendimentos e o património (separador 3) só podem ser consultados mediante pedido fundamentado e identificado, sem direito a reprodução.
- n.º 4: os campos do registo de interesses são publicados no site da EpT e no site do órgão a que o titular pertence.
- n.º 14: fora do n.º 4, a declaração não pode ser divulgada, nomeadamente num site ou numa rede social.

Questão em aberto: se republicar os campos do registo de interesses, que o n.º 4 torna públicos, está coberto pelo n.º 4 ou proibido pelo n.º 14. Até haver resposta, não republico nenhum dado da EpT: só o código e as fixtures sintéticas estão no repositório.

## O que nunca guardamos

O fetcher retira isto em memória, antes de escrever o que quer que seja em disco, num log ou no output do CI:

- qualquer número de 9 dígitos num valor mantido, substituído antes da escrita;
- a secção de filiação ou funções em entidades de natureza associativa do separador 4, inteira (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b));
- o separador 2 (dados pessoais: identificação, morada, contactos, cônjuge);
- o separador 3 (rendimentos e património);
- os anexos.

A resposta em bruto do `getdeclaration` nunca é guardada. As fixtures são sintéticas ou limpas, e os testes falham se aparecer a secção de associações, ou um valor de 9 dígitos fora dos sítios previstos, numa fixture, num seed ou num ficheiro normalizado.

## API

Base `https://api.entidadetransparencia.pt`. Todas as chamadas são `POST` sem autenticação, com um corpo JSON e `Content-Type: application/json`; o portal também envia `Origin: https://entidadetransparencia.pt`. As respostas vêm num envelope `{code, description, messageId, externalMessageId, data}`, com `code` 0 em caso de sucesso. Fazemos no máximo 1 pedido por segundo.

| Caminho | Corpo | Devolve |
|---|---|---|
| `/publicquery` | `{EntityId, RoleId, HolderId, pageNumber, pageSize, sortBy}` | Titularidades (um titular num cargo num órgão): `id`, `entityId`, `roleId`, `holderId`, `entity`, `role`, `holder`, `beginDate`, `endDate`, paginadas com `pageNumber`, `pageSize`, `pageCount`, `total`. |
| `/publicquery/getallentities` | `{}` | Todos os órgãos como `{value, label}` (4461 a 20 de outubro de 2026). |
| `/publicquery/getallroles` | `{EntityId}` | Cargos num órgão como `{value, label}`. |
| `/publicquery/getallholders` | `{EntityId, RoleId}` | Titulares como `{value, label}`; `value` é o id do titular na EpT. |
| `/publicquery/search` | `{HolderId, EntityId: [...], RoleId: [...], pageNumber, sortBy}` | As declarações de um titular: `id`, `natureType`, `stateType`, `deliveryDate`, `relatedDeclarationId`. |
| `/publicquery/getdeclaration` | `{Id, isDraft: false}` | Uma declaração: metadados (`id`, `natureType`, `stateType`, `relatedDeclarationId`, `entity`, `role`, `holder`, `holderId`, `entityId`, `roleId`, `startDate`, `endDate`, `submitedDate`, `unavailableSections`) e `data.value`, os separadores indexados por GUID. |

Órgãos e cargos da AR:

| EntityId | Designação | Abrange | Cargos |
|---|---|---|---|
| 510 | Assembleia da República | Titularidades antes da XVII (desde 2021, portanto XIV a XVI) | Deputado 8, Deputada 232, Presidente da Assembleia da República 2, Vice-Presidente 13, Vogal 18 |
| 4508 | Assembleia da República - XVII Legislatura | XVII | Deputado 8, Deputada 232, Presidente 12, Presidente da Assembleia da República 2 |

A 20 de outubro de 2026, a entidade 4508 tinha 322 titularidades e a 510 tinha 559; 263 e 427 titulares distintos como Deputado ou Deputada, 506 no total. O mesmo id de titular é usado nos dois órgãos.

Enumerações, tiradas do código do portal:

- `natureType`: 1 initial, 2 modification, 4 cessation, 8 final, 16 replace, 32 reElection.
- `stateType`: 1 draft, 2 pendingVerification, 4 notPublished, 8 published, 16 canceled, 32 modified, 64 replaced.

As datas são texto ISO em UTC (`2025-06-01T23:00:00Z` é 2 de junho em Lisboa). Guardamos o valor em bruto e convertemos para o dia em Europe/Lisbon.

Os URL de declarações do portal (`entidadetransparencia.pt/titularidades/<ids>/declaracoes/<id>`) levam ids cifrados no browser com um salt aleatório, por isso não há um URL público estável para onde apontar.

### Separador 4: registo de interesses

O separador 4 é o GUID `1483a8d1-adca-4f39-8038-98cc6f728fcb`. O seu único grupo tem seis secções, cada uma uma lista de linhas cujas células são indexadas por `<GUID da secção>-colN` e têm `value` e `isVisible`. Só mantemos as células visíveis das colunas abaixo.

| GUID da secção | Categoria | Designação | Colunas mantidas |
|---|---|---|---|
| `2c6d9562-dea5-488b-9afe-42519c636daf` | activity | Atividades profissionais, cargos públicos, privados e sociais | col1 a col7 |
| `62fb0107-a68d-4ba2-822b-bc8adc54369b` | support | Apoios ou benefícios | col1 a col5, col7 a col9 |
| `b1f8c095-fe0c-4bb3-b493-902dc0c31232` | service | Serviços prestados | col1 a col5, col7, col8 |
| `9b58c917-b14c-4eed-9b3c-40c3d99d45da` | society | Sociedades | col1 a col6, col8 |
| `fd85f91f-2803-41bc-b315-ede3a4a66d4e` | other_situation | Outras situações | col1 a col4, col6 |

A sexta secção, `cd0e811a-d9bb-49ee-b0f0-1dae0680eb22` (Filiação ou funções em entidades de natureza associativa), é descartada inteira, sem ler nenhuma célula, porque fica fora do acesso público (Regulamento da EpT n.º 258/2024, art. 15.º, n.º 1, al. b)). Se aparecer num ficheiro guardado, a verificação falha. Um GUID de secção desconhecido é um erro, não algo que se salta, para que uma alteração no formulário seja detetada. A EpT publica a Remuneração como `1` ou `0` sem a documentar, por isso fica como `paid_raw` e `is_paid` fica nulo.

## Correspondência entre titulares e deputados da AR

A EpT não tem id da AR. O `seed_ept_holders` (#47) faz corresponder cada id de titular da EpT a um `cadastro_id` pelo nome completo normalizado, comparado com a InformacaoBase (XVII para a entidade 4508, XIV a XVI para a 510), com uma correção mantida à mão para cada titular que a comparação de nomes deixa sem correspondência ou ambíguo. O RegistoBiografico da XVI é uma cópia do registo da XVII (ver [lacunas conhecidas](../known-gaps.md)), por isso não é usado para a 510.

## Nos marts

As declarações da XVI e da XVII entram em `interest_declarations` e `interests` com `source = 'ept'` e `format_version = 'EPT'` (#48). As colunas da AR vêm primeiro e pela mesma ordem; as colunas próprias da EpT vêm depois e são nulas nas linhas da AR. As declarações da entidade 510 anteriores à XVI ficam só em `stg_ept_registo_interesses__declarations`, porque a AR já as publica. O que muda face à AR está nas [lacunas conhecidas](../known-gaps.md#registo-de-interesses-da-ept-xvi-e-xvii) e no [dicionário de dados](../dictionary/interests.md).

A publicação de dados deixa de fora as linhas com `source = 'ept'`, que não estão cobertas pela CC BY 4.0, e conta-as em `excluded_sources` no `manifest.json`. Os marts continuam a tê-las no build local.

## Ordem de construção

1. #43: esta página.
2. #44: fetcher para as entidades 510 e 4508, só metadados e separador 4, limpos em memória.
3. #46: parser de staging.
4. #45: o conjunto de dados `ept_registo_interesses` no data-sync, em espera até à resposta da EpT.
5. #47: seed de correspondência entre titulares e `cadastro_id`.
6. #48: os marts unificados.
7. #49: dicionário, lacunas conhecidas e notas de publicação (esta atualização).
