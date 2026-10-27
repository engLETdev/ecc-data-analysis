# Contexto do projeto

## Objetivo

Construir uma aplicação de análise de dados a partir de bases que serão
disponibilizadas pela solicitante, preservando o ECC como referência versionada
de engenharia. Formatos, domínios e indicadores ainda não foram definidos.

## Referência e responsabilidades

| Item | Definição |
| --- | --- |
| Repositório de trabalho | `https://github.com/engLETdev/ecc-data-analysis` |
| Origem ECC | `https://github.com/affaan-m/ECC` |
| Commit de referência | `25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b` |
| Versão declarada do ECC | 2.2.3 |
| Branch de implementação | `feat/data-analysis-foundation` |
| Pacote da aplicação | `examples/data-analysis/` |
| Convenções adotadas | Planejamento, TDD, revisão, tipagem, layout src/tests, contratos e rastreabilidade |
| Referências de convenções | `AGENTS.md`, regras Python, skills python-patterns/python-testing/data-throughput-accelerator/mle-workflow |

O arquivo `upstream-lock.json` identifica os arquivos e hashes efetivamente
fixados. A aplicação tem seu próprio manifesto; `src/llm` da raiz continua com
a responsabilidade de abstração de provedores LLM. Não existem chamadas de IA
no processamento desta fundação.

## Escopo desta implementação

- Configuração TOML estrita e independente do diretório de execução.
- Consulta do estado por CLI.
- Registro de identidade de arquivos locais por SHA-256 e tamanho.
- Histórico de fontes com identidade lógica, caminho relativo e referência ECC.
- Repetição idempotente, escrita atômica e exclusão de escritores concorrentes.
- Testes unitários, de integração e de CLI, com dados sintéticos.
- Verificação isolada por lint, formatação e cobertura mínima de 80%.

O registro de fontes não significa aprovação da qualidade dos dados. Ingestão
tabular, transformação, indicadores, gráficos, dashboard e agendamento de
atualizações dependem dos contratos e das bases futuras.

## Rotina para retomar o trabalho

1. Confirmar repositório de trabalho, branch e SHA atual.
2. Ler `AGENTS.md`, este contexto e `upstream-lock.json`.
3. Consultar os módulos existentes antes de propor novas funções ou dependências.
4. Conferir o contrato de dados e as definições dos indicadores envolvidos.
5. Trabalhar em branch específica, registrar decisões e executar os testes adequados.
6. Apresentar o diff e as evidências em pull request para revisão.

Não registrar automaticamente informações privadas em instruções, fixtures,
logs, commits ou pull requests. Originais e manifestos de execução ficam fora
do versionamento. O repositório de trabalho é público e pertence à conta
`engLETdev`; o acesso de escrita pela integração GitHub foi confirmado. Toda
alteração deve ser apresentada em uma branch específica e em pull request
destinado à `main` desse repositório, para revisão antes de qualquer merge.

## Próximos insumos

- Bases ou amostras representativas e autorização de uso.
- Significado das colunas, unidades, período, granularidade e chaves.
- Volume aproximado e frequência de atualização esperada.
- Perguntas analíticas e definições dos indicadores.
- Regras para nulos, duplicatas, rejeições, retenção e acesso.

Nenhum domínio específico, incluindo energia, foi presumido nesta fundação.
