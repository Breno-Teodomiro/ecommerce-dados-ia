# Catálogo de Dados — E-commerce Analytics

Este documento descreve as 3 views gold disponíveis para consulta.
Use estas tabelas para responder perguntas sobre o e-commerce.

---

## 1. `public_gold_sales.vendas_temporais`

Tabela de fatos de vendas com dimensões de tempo pré-calculadas.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_venda` | STRING | Identificador único da venda |
| `data_venda` | DATE | Data da venda |
| `ano_venda` | INT | Ano (ex: 2025) |
| `mes_venda` | INT | Mês (1-12) |
| `hora_venda` | INT | Hora do dia (0-23) |
| `dia_semana_nome` | STRING | Nome do dia: Segunda, Terça, ..., Domingo |
| `canal_venda` | STRING | Canal: `ecommerce`, `loja_fisica`, `marketplace` |
| `id_cliente` | STRING | ID do cliente |
| `nome_cliente` | STRING | Nome completo do cliente |
| `estado` | STRING | UF do cliente (ex: SP, RJ) |
| `id_produto` | STRING | ID do produto |
| `nome_produto` | STRING | Nome do produto |
| `categoria` | STRING | Categoria do produto |
| `quantidade` | INT | Quantidade vendida |
| `preco_unitario` | FLOAT | Preço unitário na venda |
| `receita_total` | FLOAT | `quantidade × preco_unitario` |
| `total_vendas` | INT | Nº total de vendas naquele dia |
| `total_clientes_unicos` | INT | Clientes únicos naquele dia |
| `ticket_medio` | FLOAT | Ticket médio do dia |

**Exemplo de query:**
```sql
SELECT data_venda, SUM(receita_total) AS receita
FROM public_gold_sales.vendas_temporais
GROUP BY data_venda ORDER BY data_venda DESC LIMIT 7
```

---

## 2. `public_gold_cs.clientes_segmentacao`

Um registro por cliente com métricas acumuladas de compras.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_cliente` | STRING | ID do cliente |
| `nome_cliente` | STRING | Nome completo |
| `estado` | STRING | UF |
| `pais` | STRING | País (sempre Brasil) |
| `receita_total` | FLOAT | Receita total acumulada do cliente |
| `total_compras` | INT | Número total de compras |
| `ticket_medio` | FLOAT | Ticket médio por compra |
| `ranking_receita` | INT | Posição no ranking (1 = maior receita) |
| `segmento_cliente` | STRING | `VIP` (top 10), `TOP_TIER` (top 11-25), `REGULAR` (demais) |

**Exemplo de query:**
```sql
SELECT segmento_cliente, COUNT(*) AS clientes, SUM(receita_total) AS receita
FROM public_gold_cs.clientes_segmentacao
GROUP BY segmento_cliente ORDER BY receita DESC
```

---

## 3. `public_gold_pricing.precos_competitividade`

Um registro por produto com comparação de preços vs. concorrentes.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_produto` | STRING | ID do produto |
| `nome_produto` | STRING | Nome do produto |
| `categoria` | STRING | Categoria |
| `marca` | STRING | Marca |
| `nosso_preco` | FLOAT | Preço atual no nosso e-commerce |
| `preco_medio_concorrentes` | FLOAT | Preço médio dos concorrentes |
| `preco_minimo_concorrentes` | FLOAT | Menor preço entre concorrentes |
| `preco_maximo_concorrentes` | FLOAT | Maior preço entre concorrentes |
| `diferenca_percentual_vs_media` | FLOAT | `(nosso_preco - média) / média × 100` |
| `classificacao_preco` | STRING | `MAIS_CARO_QUE_TODOS`, `ACIMA_DA_MEDIA`, `NA_MEDIA`, `ABAIXO_DA_MEDIA`, `MAIS_BARATO_QUE_TODOS` |
| `quantidade_total` | INT | Quantidade total vendida |
| `receita_total` | FLOAT | Receita total gerada pelo produto |

**Exemplo de query:**
```sql
SELECT nome_produto, nosso_preco, preco_medio_concorrentes, diferenca_percentual_vs_media
FROM public_gold_pricing.precos_competitividade
WHERE classificacao_preco = 'MAIS_CARO_QUE_TODOS'
ORDER BY diferenca_percentual_vs_media DESC LIMIT 10
```

---

## Regras de Negócio

- **Segmentação de clientes:** VIP = top 10 por receita; TOP_TIER = posições 11-25; REGULAR = demais
- **Classificação de preço:** baseada no preço atual vs. range de concorrentes (min/max/média)
- **Receita:** sempre `quantidade × preco_unitario` — não há desconto aplicado nas tabelas
- **Concorrentes monitorados:** Mercado Livre, Amazon, Shopee (e outros)
- **Período dos dados:** aproximadamente Dez/2025 a Jan/2026
