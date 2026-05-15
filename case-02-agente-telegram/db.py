"""
db.py — Conexão DuckDB e views gold para o agente de dados.
Aceita apenas queries SELECT/WITH por segurança.
"""

import os
import re
import duckdb
import pandas as pd
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
POSTGRES_URL = os.getenv("POSTGRES_URL", "")

BASE_DIR    = Path(__file__).parent.parent / "arquivos_parquet"
VENDAS_PATH  = str(BASE_DIR / "vendas.parquet")
CLIENTES_PATH= str(BASE_DIR / "clientes.parquet")
PRODUTOS_PATH= str(BASE_DIR / "produtos.parquet")
PRECOS_PATH  = str(BASE_DIR / "preco_competidores.parquet")

_ALLOWED = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


def _build_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    conn.execute(f"CREATE VIEW vendas_raw   AS SELECT * FROM read_parquet('{VENDAS_PATH}')")
    conn.execute(f"CREATE VIEW clientes_raw AS SELECT * FROM read_parquet('{CLIENTES_PATH}')")
    conn.execute(f"CREATE VIEW produtos_raw AS SELECT * FROM read_parquet('{PRODUTOS_PATH}')")
    conn.execute(f"CREATE VIEW precos_raw   AS SELECT * FROM read_parquet('{PRECOS_PATH}')")

    # Criar schemas para suportar notação com ponto (public_gold_sales.xxx)
    conn.execute("CREATE SCHEMA IF NOT EXISTS public_gold_sales")
    conn.execute("CREATE SCHEMA IF NOT EXISTS public_gold_cs")
    conn.execute("CREATE SCHEMA IF NOT EXISTS public_gold_pricing")

    conn.execute("""
        CREATE VIEW gold_vendas_base AS
        SELECT
            v.id_venda,
            v.data_venda::DATE                                   AS data_venda,
            EXTRACT(year  FROM v.data_venda)::INT                AS ano_venda,
            EXTRACT(month FROM v.data_venda)::INT                AS mes_venda,
            EXTRACT(hour  FROM v.data_venda)::INT                AS hora_venda,
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
            v.quantidade,
            v.preco_unitario,
            v.quantidade * v.preco_unitario                      AS receita_total,
            COUNT(*) OVER (PARTITION BY v.data_venda::DATE)      AS total_vendas,
            COUNT(DISTINCT v.id_cliente) OVER (
                PARTITION BY v.data_venda::DATE)                 AS total_clientes_unicos,
            AVG(v.quantidade * v.preco_unitario) OVER (
                PARTITION BY v.data_venda::DATE)                 AS ticket_medio
        FROM vendas_raw   v
        LEFT JOIN clientes_raw c ON c.id_cliente = v.id_cliente
        LEFT JOIN produtos_raw p ON p.id_produto = v.id_produto
    """)
    conn.execute("CREATE VIEW public_gold_sales.vendas_temporais AS SELECT * FROM gold_vendas_base")

    conn.execute("""
        CREATE VIEW gold_clientes_base AS
        WITH stats AS (
            SELECT id_cliente,
                SUM(quantidade * preco_unitario) AS receita_total,
                COUNT(DISTINCT id_venda)          AS total_compras,
                AVG(quantidade * preco_unitario)  AS ticket_medio
            FROM vendas_raw GROUP BY id_cliente
        ),
        ranked AS (
            SELECT *, ROW_NUMBER() OVER (ORDER BY receita_total DESC) AS ranking_receita FROM stats
        )
        SELECT c.id_cliente, c.nome_cliente, c.estado, c.pais,
               r.receita_total, r.total_compras, r.ticket_medio, r.ranking_receita,
               CASE WHEN r.ranking_receita <= 10 THEN 'VIP'
                    WHEN r.ranking_receita <= 25 THEN 'TOP_TIER'
                    ELSE 'REGULAR' END AS segmento_cliente
        FROM clientes_raw c LEFT JOIN ranked r ON r.id_cliente = c.id_cliente
    """)
    conn.execute("CREATE VIEW public_gold_cs.clientes_segmentacao AS SELECT * FROM gold_clientes_base")

    conn.execute("""
        CREATE VIEW gold_pricing_base AS
        WITH latest AS (
            SELECT id_produto, nome_concorrente, preco_concorrente,
                   ROW_NUMBER() OVER (PARTITION BY id_produto, nome_concorrente ORDER BY data_coleta DESC) rn
            FROM precos_raw
        ),
        conc AS (
            SELECT id_produto,
                AVG(preco_concorrente) AS preco_medio_concorrentes,
                MIN(preco_concorrente) AS preco_minimo_concorrentes,
                MAX(preco_concorrente) AS preco_maximo_concorrentes
            FROM latest WHERE rn=1 GROUP BY id_produto
        ),
        vp AS (
            SELECT id_produto,
                SUM(quantidade) AS quantidade_total,
                SUM(quantidade*preco_unitario) AS receita_total
            FROM vendas_raw GROUP BY id_produto
        )
        SELECT p.id_produto, p.nome_produto, p.categoria, p.marca,
               p.preco_atual AS nosso_preco,
               c.preco_medio_concorrentes, c.preco_minimo_concorrentes, c.preco_maximo_concorrentes,
               ROUND((p.preco_atual - c.preco_medio_concorrentes)/c.preco_medio_concorrentes*100,2)
                   AS diferenca_percentual_vs_media,
               CASE WHEN p.preco_atual > c.preco_maximo_concorrentes THEN 'MAIS_CARO_QUE_TODOS'
                    WHEN p.preco_atual > c.preco_medio_concorrentes  THEN 'ACIMA_DA_MEDIA'
                    WHEN p.preco_atual < c.preco_minimo_concorrentes THEN 'MAIS_BARATO_QUE_TODOS'
                    WHEN p.preco_atual < c.preco_medio_concorrentes  THEN 'ABAIXO_DA_MEDIA'
                    ELSE 'NA_MEDIA' END AS classificacao_preco,
               COALESCE(vp.quantidade_total,0) AS quantidade_total,
               COALESCE(vp.receita_total,0)    AS receita_total
        FROM produtos_raw p
        LEFT JOIN conc c  ON c.id_produto = p.id_produto
        LEFT JOIN vp   vp ON vp.id_produto = p.id_produto
        WHERE c.id_produto IS NOT NULL
    """)
    conn.execute("CREATE VIEW public_gold_pricing.precos_competitividade AS SELECT * FROM gold_pricing_base")

    return conn


def execute_query(sql: str) -> pd.DataFrame:
    """Executa query SQL. Apenas SELECT e WITH são permitidos."""
    if not _ALLOWED.match(sql.strip()):
        raise ValueError("❌ Apenas queries SELECT ou WITH são permitidas.")
    
    if POSTGRES_URL:
        try:
            conn = psycopg2.connect(POSTGRES_URL)
            df = pd.read_sql_query(sql, conn)
            conn.close()
            return df
        except Exception as e:
            raise RuntimeError(f"Erro ao executar query no Supabase: {e}")
    else:
        conn = _build_conn()
        try:
            return conn.execute(sql).df()
        except Exception as e:
            raise RuntimeError(f"Erro ao executar query: {e}")


def get_schema() -> str:
    """Retorna o schema das views gold como string para o system prompt."""
    return open(Path(__file__).parent / ".llm" / "database.md", encoding="utf-8").read()
