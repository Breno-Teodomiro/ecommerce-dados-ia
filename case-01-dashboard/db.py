"""
db.py — Conexão DuckDB e criação das views gold a partir dos Parquets locais.
"""

import os
import duckdb
import pandas as pd
import psycopg2
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
POSTGRES_URL = os.getenv("POSTGRES_URL", "")

# Caminho base dos arquivos Parquet (relativo a este arquivo)
BASE_DIR = Path(__file__).parent.parent / "arquivos_parquet"

VENDAS_PATH     = str(BASE_DIR / "vendas.parquet")
CLIENTES_PATH   = str(BASE_DIR / "clientes.parquet")
PRODUTOS_PATH   = str(BASE_DIR / "produtos.parquet")
PRECOS_PATH     = str(BASE_DIR / "preco_competidores.parquet")


def get_conn() -> duckdb.DuckDBPyConnection:
    """Retorna conexão DuckDB in-memory com as views gold registradas."""
    conn = duckdb.connect(":memory:")

    # ── Registrar parquets como views brutas ──────────────────────────────────
    conn.execute(f"CREATE VIEW vendas_raw     AS SELECT * FROM read_parquet('{VENDAS_PATH}')")
    conn.execute(f"CREATE VIEW clientes_raw   AS SELECT * FROM read_parquet('{CLIENTES_PATH}')")
    conn.execute(f"CREATE VIEW produtos_raw   AS SELECT * FROM read_parquet('{PRODUTOS_PATH}')")
    conn.execute(f"CREATE VIEW precos_raw     AS SELECT * FROM read_parquet('{PRECOS_PATH}')")

    # ── Gold 1: vendas_temporais ──────────────────────────────────────────────
    conn.execute("""
        CREATE VIEW gold_vendas AS
        SELECT
            v.id_venda,
            v.data_venda::DATE                                   AS data_venda,
            EXTRACT(year  FROM v.data_venda)::INT                AS ano_venda,
            EXTRACT(month FROM v.data_venda)::INT                AS mes_venda,
            EXTRACT(hour  FROM v.data_venda)::INT                AS hora_venda,
            DAYOFWEEK(v.data_venda)                              AS dia_semana_num,
            CASE DAYOFWEEK(v.data_venda)
                WHEN 1 THEN 'Domingo'   WHEN 2 THEN 'Segunda'
                WHEN 3 THEN 'Terça'     WHEN 4 THEN 'Quarta'
                WHEN 5 THEN 'Quinta'    WHEN 6 THEN 'Sexta'
                WHEN 7 THEN 'Sábado'
            END                                                  AS dia_semana_nome,
            v.canal_venda,
            v.id_cliente,
            c.nome_cliente,
            c.estado,
            v.id_produto,
            p.nome_produto,
            p.categoria,
            p.marca,
            v.quantidade,
            v.preco_unitario,
            v.quantidade * v.preco_unitario                      AS receita
        FROM vendas_raw   v
        LEFT JOIN clientes_raw c ON c.id_cliente = v.id_cliente
        LEFT JOIN produtos_raw p ON p.id_produto  = v.id_produto
    """)

    # ── Gold 2: clientes_segmentacao ─────────────────────────────────────────
    conn.execute("""
        CREATE VIEW gold_clientes AS
        WITH stats AS (
            SELECT
                v.id_cliente,
                SUM(v.quantidade * v.preco_unitario) AS receita_total,
                COUNT(DISTINCT v.id_venda)           AS total_compras,
                AVG(v.quantidade * v.preco_unitario) AS ticket_medio
            FROM vendas_raw v
            GROUP BY v.id_cliente
        ),
        ranked AS (
            SELECT
                id_cliente,
                receita_total,
                total_compras,
                ticket_medio,
                ROW_NUMBER() OVER (ORDER BY receita_total DESC) AS ranking_receita
            FROM stats
        )
        SELECT
            c.id_cliente,
            c.nome_cliente,
            c.estado,
            c.pais,
            c.data_cadastro::DATE                               AS data_cadastro,
            r.receita_total,
            r.total_compras,
            r.ticket_medio,
            r.ranking_receita,
            CASE
                WHEN r.ranking_receita <= 10 THEN 'VIP'
                WHEN r.ranking_receita <= 25 THEN 'TOP_TIER'
                ELSE 'REGULAR'
            END AS segmento_cliente
        FROM clientes_raw c
        LEFT JOIN ranked r ON r.id_cliente = c.id_cliente
    """)

    # ── Gold 3: precos_competitividade ────────────────────────────────────────
    conn.execute("""
        CREATE VIEW gold_pricing AS
        WITH latest_prices AS (
            SELECT
                id_produto,
                nome_concorrente,
                preco_concorrente,
                ROW_NUMBER() OVER (
                    PARTITION BY id_produto, nome_concorrente
                    ORDER BY data_coleta DESC
                ) AS rn
            FROM precos_raw
        ),
        concorrentes AS (
            SELECT
                id_produto,
                AVG(preco_concorrente)  AS preco_medio_concorrentes,
                MIN(preco_concorrente)  AS preco_minimo_concorrentes,
                MAX(preco_concorrente)  AS preco_maximo_concorrentes,
                COUNT(*)                AS qtd_concorrentes
            FROM latest_prices
            WHERE rn = 1
            GROUP BY id_produto
        ),
        vendas_prod AS (
            SELECT
                id_produto,
                SUM(quantidade)                      AS quantidade_total,
                SUM(quantidade * preco_unitario)     AS receita_total
            FROM vendas_raw
            GROUP BY id_produto
        )
        SELECT
            p.id_produto,
            p.nome_produto,
            p.categoria,
            p.marca,
            p.preco_atual                                           AS nosso_preco,
            c.preco_medio_concorrentes,
            c.preco_minimo_concorrentes,
            c.preco_maximo_concorrentes,
            c.qtd_concorrentes,
            ROUND(
                (p.preco_atual - c.preco_medio_concorrentes)
                / c.preco_medio_concorrentes * 100, 2
            )                                                       AS diferenca_percentual_vs_media,
            CASE
                WHEN p.preco_atual > c.preco_maximo_concorrentes THEN 'MAIS_CARO_QUE_TODOS'
                WHEN p.preco_atual > c.preco_medio_concorrentes  THEN 'ACIMA_DA_MEDIA'
                WHEN p.preco_atual < c.preco_minimo_concorrentes THEN 'MAIS_BARATO_QUE_TODOS'
                WHEN p.preco_atual < c.preco_medio_concorrentes  THEN 'ABAIXO_DA_MEDIA'
                ELSE 'NA_MEDIA'
            END                                                     AS classificacao_preco,
            COALESCE(vp.quantidade_total, 0)                        AS quantidade_total,
            COALESCE(vp.receita_total,    0)                        AS receita_total
        FROM produtos_raw     p
        LEFT JOIN concorrentes c  ON c.id_produto = p.id_produto
        LEFT JOIN vendas_prod  vp ON vp.id_produto = p.id_produto
        WHERE c.id_produto IS NOT NULL
    """)

    return conn


@st.cache_data(ttl=600)
def query(sql: str) -> pd.DataFrame:
    """Executa uma query SQL e retorna DataFrame (Supabase se configurado, senão DuckDB).
    Utiliza cache para evitar esgotamento de conexões no Supabase (timeout/OperationalError)."""
    if POSTGRES_URL:
        # Usa URL do sqlalchemy para pandas (evita warning e lida melhor com transações)
        # postgresql:// -> postgresql+psycopg2://
        url_alchemy = POSTGRES_URL.replace("postgresql://", "postgresql+psycopg2://")
        from sqlalchemy import create_engine
        engine = create_engine(url_alchemy, pool_pre_ping=True)
        with engine.connect() as conn:
            df = pd.read_sql_query(sql, conn)
        engine.dispose()
        return df
    else:
        conn = get_conn()
        return conn.execute(sql).df()
