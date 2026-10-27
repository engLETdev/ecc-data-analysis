# Fundação do projeto de análise de dados

Este pacote prepara a configuração e a rastreabilidade das futuras bases de
dados. Ele usa as convenções do ECC em um projeto Python isolado, com layout
`src/`, testes próprios e dependências de desenvolvimento separadas.

O runtime usa somente a biblioteca padrão do Python. Nesta etapa, registrar
um arquivo comprova sua identidade por SHA-256 e tamanho; não valida suas
colunas, não trata registros e não calcula indicadores. As regras analíticas,
os gráficos e o dashboard serão definidos após o recebimento das bases.

## Instalação

Requer Python 3.11 ou superior. A partir da raiz do repositório:

```bash
cd examples/data-analysis
python -m venv .venv
```

Ative o ambiente conforme seu sistema:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instale as ferramentas de desenvolvimento e somente este pacote:

```bash
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
```

Não é necessário instalar o pacote LLM da raiz, Node, provedores de IA ou
conectores externos para executar esta fundação. O arquivo de lock fixa as
ferramentas e suas dependências resolvidas para o CI Linux; o backend de build
segue o requisito declarado em `pyproject.toml`.

## Configuração

O arquivo versionado `config/project.example.toml` funciona como configuração
inicial. Para personalizar caminhos, copie-o para `config/project.toml`, que
está ignorado pelo Git. O esquema é estrito: chaves desconhecidas, tipos
incorretos e valores obrigatórios ausentes são erros.

Os caminhos de armazenamento são resolvidos em relação ao diretório do TOML,
independentemente de onde o comando é executado. O exemplo mantém:

| Local | Conteúdo |
| --- | --- |
| `data/raw/` | Arquivos originais a serem registrados |
| `data/manifests/sources.json` | Histórico local de identidades das fontes |

O manifesto fica fora do diretório de originais. A pasta `data/` inteira não é
versionada. Configurações locais podem apontar para armazenamento fora do
checkout; esse local deve receber as mesmas proteções de acesso e backup.

## Comandos disponíveis

Consultar o estado não cria diretórios nem modifica o manifesto:

```bash
python -m data_analysis --config config/project.example.toml status
```

A configuração inicial retorna `state: "awaiting_datasets"`,
`registered_sources: 0` e `analysis_ready: false`. O campo
`registered_sources` conta as versões registradas, identificadas por fonte e
hash. O registro de arquivos não altera `analysis_ready`, pois a validação
analítica ainda depende das bases e de seus contratos.

Após disponibilizar um arquivo em `data/raw/`, registre sua identidade:

```bash
python -m data_analysis --config config/project.example.toml register-source --source-id base-01 --file data/raw/arquivo.csv
```

O caminho passado em `--file` é relativo ao diretório atual do terminal ou pode
ser absoluto. Ele precisa resolver para um arquivo dentro do `raw_dir`
configurado. Um link simbólico que aponta para fora desse diretório é rejeitado.

O comando também está disponível como `data-analysis` após a instalação. A
saída de sucesso é JSON. Falhas retornam código diferente de zero e uma
mensagem em stderr, sem imprimir o conteúdo da base.

## Identidade e reprocessamento

O identificador lógico da fonte deve ter entre 1 e 64 caracteres ASCII,
começar com letra ou número e usar somente letras, números, ponto, hífen ou
sublinhado. Ele não deve conter nomes de pessoas ou outras informações privadas.

A identidade de um registro é a dupla **identificador lógico + SHA-256**.
Registrar novamente essa dupla não cria outra entrada nem altera os bytes do
manifesto. Um conteúdo diferente para o mesmo identificador gera uma nova
versão. O mesmo conteúdo pode pertencer a fontes lógicas distintas.

O manifesto registra caminho relativo ao diretório de originais, tamanho,
hash, data de registro e referência ECC. A primeira localização registrada é
preservada quando a mesma dupla é encontrada por outro caminho. O arquivo
original não é copiado nem alterado.

A gravação usa substituição atômica e um lock exclusivo ao lado do manifesto.
Esta fundação trabalha com um escritor por manifesto: outra gravação
concorrente é rejeitada. Um manifesto inválido não é apagado ou recriado
silenciosamente. Um lock remanescente após interrupção deve ser investigado
antes de sua remoção; não remova o lock de um processo em execução.

Use um diretório local sob seu controle. A implementação detecta alterações
observáveis do arquivo durante a leitura e revalida sua localização antes do
registro. Esses controles não constituem uma sandbox contra terceiros com
controle contínuo do sistema de arquivos.

## Verificação

Execute os comandos dentro de `examples/data-analysis/`:

```bash
python -m ruff check src tests
python -m ruff format --check src tests
python -m pytest --cov=data_analysis --cov-report=term-missing --cov-fail-under=80
```

Os testes usam somente arquivos sintéticos temporários. O workflow
`.github/workflows/data-analysis.yml` executa a verificação isolada em Python
3.11 e 3.12, sem instalar o pacote Python da raiz. O limite de 80% se aplica ao
código deste pacote, não ao ECC inteiro.

A configuração de cobertura agrega os subprocessos dos testes da CLI por
meio de `patch = ["subprocess"]`, recurso da versão de Coverage fixada no lock.
Assim, o relatório inclui os caminhos executados em processos separados.

## Referência ECC e continuidade

`upstream-lock.json` fixa a origem, o commit e os hashes das convenções do ECC
adotadas. O ponto de partida é o commit
`25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b` de
[affaan-m/ECC](https://github.com/affaan-m/ECC).

Leia [o contexto do projeto](docs/project-context.md) no início de cada sessão.
O [contrato de dados](docs/data-contract.md) e o
[catálogo de indicadores](docs/indicators.md) serão preenchidos com informações
validadas após a entrega das bases. A URL do repositório, sozinha, não carrega
automaticamente todos os arquivos em sessões futuras.
