# Contrato de dados a definir

Estado: aguardando as bases e suas definições. Este documento é um modelo de
levantamento; seus campos pendentes não são regras implementadas no pacote.

## Identificação da fonte

| Campo | Valor validado |
| --- | --- |
| Identificador lógico | Pendente |
| Responsável pela definição | Pendente |
| Formato, encoding e delimitador | Pendente |
| Aba/tabela, quando aplicável | Pendente |
| Granularidade de cada registro | Pendente |
| Período e fuso horário | Pendente |
| Chaves e política de duplicatas | Pendente |
| Frequência e atraso aceitável | Pendente |
| Política de acesso e retenção | Pendente |

## Colunas

Preencher uma linha por coluna após inspecionar a base. Nenhuma coluna foi
inventada para esta etapa.

| Coluna | Significado | Tipo | Unidade | Nulos permitidos | Domínio/faixa | Regra de validação |
| --- | --- | --- | --- | --- | --- | --- |

## Reconciliação e aceite

Definir as contagens, totais e períodos que serão comparados com a fonte,
incluindo tolerâncias justificadas. Separar registros aceitos, duplicados,
rejeitados e falhas de leitura. Execuções parciais devem ter estado explícito.

Antes da ingestão analítica, validar:

1. A identidade do arquivo e a referência de sua versão.
2. O esquema, as unidades e as regras de datas.
3. Os critérios de nulos, categorias e duplicatas.
4. O destino e a evidência dos registros rejeitados.
5. Os testes com casos conhecidos e a reconciliação dos resultados.

O manifesto de fontes da fundação registra identidade e proveniência. Ele
não substitui este contrato e não confirma, por si só, a qualidade da base.
