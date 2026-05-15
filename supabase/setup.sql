-- supabase/setup.sql
-- Execute este script no SQL Editor do Supabase (uma vez) antes de rodar load_data.py

-- ── Schemas ───────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS public_gold_sales;
CREATE SCHEMA IF NOT EXISTS public_gold_cs;
CREATE SCHEMA IF NOT EXISTS public_gold_pricing;

-- ── Tabela 1: vendas_temporais ────────────────────────────────────────────────
DROP TABLE IF EXISTS public_gold_sales.vendas_temporais;
CREATE TABLE public_gold_sales.vendas_temporais (
    id_venda                VARCHAR PRIMARY KEY,
    data_venda              DATE,
    ano_venda               SMALLINT,
    mes_venda               SMALLINT,
    hora_venda              SMALLINT,
    dia_semana_nome         VARCHAR(10),
    canal_venda             VARCHAR(50),
    id_cliente              VARCHAR,
    nome_cliente            VARCHAR,
    estado                  CHAR(2),
    id_produto              VARCHAR,
    nome_produto            VARCHAR,
    categoria               VARCHAR,
    quantidade              INTEGER,
    preco_unitario          NUMERIC(10,2),
    receita_total           NUMERIC(12,2),
    total_vendas            INTEGER,
    total_clientes_unicos   INTEGER,
    ticket_medio            NUMERIC(10,2)
);

-- ── Tabela 2: clientes_segmentacao ────────────────────────────────────────────
DROP TABLE IF EXISTS public_gold_cs.clientes_segmentacao;
CREATE TABLE public_gold_cs.clientes_segmentacao (
    id_cliente              VARCHAR PRIMARY KEY,
    nome_cliente            VARCHAR,
    estado                  CHAR(2),
    pais                    VARCHAR(50),
    receita_total           NUMERIC(12,2),
    total_compras           INTEGER,
    ticket_medio            NUMERIC(10,2),
    ranking_receita         INTEGER,
    segmento_cliente        VARCHAR(20)
);

-- ── Tabela 3: precos_competitividade ──────────────────────────────────────────
DROP TABLE IF EXISTS public_gold_pricing.precos_competitividade;
CREATE TABLE public_gold_pricing.precos_competitividade (
    id_produto                      VARCHAR PRIMARY KEY,
    nome_produto                    VARCHAR,
    categoria                       VARCHAR,
    marca                           VARCHAR,
    nosso_preco                     NUMERIC(10,2),
    preco_medio_concorrentes        NUMERIC(10,2),
    preco_minimo_concorrentes       NUMERIC(10,2),
    preco_maximo_concorrentes       NUMERIC(10,2),
    diferenca_percentual_vs_media   NUMERIC(8,2),
    classificacao_preco             VARCHAR(30),
    quantidade_total                INTEGER,
    receita_total                   NUMERIC(12,2)
);
