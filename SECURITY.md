# Segurança

## Como reportar

Não abra uma issue pública para reportar uma vulnerabilidade ou uma fuga de dados.

Use o reporte privado de vulnerabilidades do GitHub:

1. Abra o separador **Security** deste repositório.
2. Carregue em **Report a vulnerability**.
3. Descreva o problema, onde o encontrou e, se possível, como o reproduzir.

Ligação direta: <https://github.com/rfsbraz/parlamento-aberto/security/advisories/new>

O reporte fica visível apenas para quem mantém o repositório.

## O que reportar por esta via

- Vulnerabilidades no código, nos workflows do GitHub Actions ou nas dependências.
- Um segredo ou token publicado no repositório ou no histórico.
- Dados que a lei não permite publicar e que aparecem no repositório, no histórico ou numa release de dados: por exemplo um NIF pessoal, uma morada, contactos, ou uma célula dos separadores 2 (dados pessoais) ou 3 (rendimentos e património) que a Entidade para a Transparência esconde.

Não copie o dado pessoal para o reporte. Indique o ficheiro, o commit ou a release e o identificador do registo.

## Correções de dados

Um dado errado ou desatualizado que a fonte oficial publica não é uma vulnerabilidade. Use o formulário [Correção de dados](https://github.com/rfsbraz/parlamento-aberto/issues/new?template=correcao-de-dados.yml). Pedidos de correção ou remoção de dados pessoais podem usar o mesmo formulário ou o reporte privado acima.

## Versões suportadas

Só o ramo `main` e a release de dados mais recente recebem correções.
