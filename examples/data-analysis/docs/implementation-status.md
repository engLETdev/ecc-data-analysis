# Estado da fundação

Implementação na branch `feat/data-analysis-foundation` do repositório
`engLETdev/ecc-data-analysis`, a partir do commit ECC
`25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b`.

## Entregas verificadas

- Pacote Python isolado e instalável, sem dependências externas em execução.
- Configuração TOML estrita, com caminhos relativos ao arquivo de configuração.
- CLI de consulta de estado e registro de identidade dos arquivos originais.
- SHA-256 por streaming, tamanho e verificação de alterações observáveis.
- Histórico local idempotente por identificador lógico e hash.
- Manifesto validado, escrita atômica e lock exclusivo por escritor.
- Referência ECC com dez arquivos e hashes SHA-256 conferidos.
- Testes unitários, de integração e E2E com arquivos sintéticos temporários.
- CI própria configurada para Python 3.11 e 3.12, com permissões de leitura.

## Evidências locais

A execução final aprovou **72 testes**, com **91,89% de cobertura**, incluindo
branches e processos da CLI. Ruff, formatação e instalação editável foram
verificados. Os relatórios de execução ficam em `reports/`, ignorado pelo Git.

A revisão independente identificou e levou à correção das trocas de arquivos
por links externos durante o registro e do tratamento de JSON muito aninhado.
Regressões também verificam preservação do manifesto e limpeza de arquivos
temporários e locks após uma falha na substituição atômica.

Os testes locais foram executados com Python 3.12. A matriz de CI em 3.11 e
3.12 está configurada; o seu resultado remoto precisa ser consultado após a
publicação. Não foi executada a suíte completa do núcleo ECC, que não recebeu
alterações de implementação nesta etapa.

## Continuação

O fork `https://github.com/engLETdev/ecc-data-analysis` está acessível pela
integração GitHub, com permissão de escrita confirmada. As mudanças desta
fundação são destinadas à branch `feat/data-analysis-foundation` e à revisão
por pull request contra a `main` do próprio fork. A aprovação e o merge ficam
para uma etapa posterior à revisão.

O recebimento das bases permitirá definir contratos de colunas, unidades,
datas, chaves e regras de qualidade. Ingestão tabular, tratamentos, indicadores,
gráficos e dashboard ainda não estão implementados.
