"""
app.py — Dashboard Streamlit com 3 páginas para diretores de e-commerce.
Dados: DuckDB lendo Parquets locais via db.py
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from db import query

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="E-commerce Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS customizado ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29, #302b63, #24243e);
    }
    [data-testid="stSidebar"] * { color: #e8e8f0 !important; }
    [data-testid="stSidebar"] .stRadio > label { font-weight: 600; }

    /* Métricas */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1rem 1.2rem;
    }
    [data-testid="stMetricLabel"] { font-size: 0.78rem !important; color: #9090b0 !important; }
    [data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 700 !important; }

    /* Background */
    .stApp { background-color: #0e0e1a; }

    /* Título da página */
    h1 { color: #e8e8ff; font-weight: 700; }
    h2, h3 { color: #c8c8e8; }

    /* Cards de gráficos */
    .plot-container { border-radius: 12px; }

    /* Separadores */
    hr { border-color: rgba(255,255,255,0.08); }
</style>
""", unsafe_allow_html=True)

# ── Paleta de cores consistente ───────────────────────────────────────────────
COLORS = {
    "primary":    "#7c6fcd",
    "secondary":  "#56ccf2",
    "accent":     "#f2994a",
    "danger":     "#eb5757",
    "success":    "#6fcf97",
    "chart": ["#7c6fcd", "#56ccf2", "#f2994a", "#6fcf97", "#eb5757",
              "#bb6bd9", "#2f80ed", "#f2c94c", "#219653", "#e05252"],
}

PLOTLY_TEMPLATE = dict(
    paper_bgcolor="rgba(20,20,35,0)",
    plot_bgcolor="rgba(20,20,35,0)",
    font=dict(family="Inter", color="#c8c8e8", size=12),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)"),
)


def apply_layout(fig, title="", height=360):
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color="#d8d8f0"), x=0),
        height=height,
        margin=dict(l=10, r=10, t=45, b=10),
        **PLOTLY_TEMPLATE,
    )
    return fig


def fmt_brl(value: float) -> str:
    """Formata valor em R$ com separadores brasileiros."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 E-commerce\n### Analytics")
    st.markdown("---")
    pagina = st.radio(
        "Navegar para",
        ["🛒 Vendas", "👥 Clientes", "💰 Pricing"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("Dados: DuckDB + Parquet local")
    st.caption("Atualizado em tempo real")


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — VENDAS
# ═══════════════════════════════════════════════════════════════════════════════
if pagina == "🛒 Vendas":
    st.title("🛒 Comercial — Análise de Vendas")
    st.markdown("Visão consolidada de receita, volume e padrões temporais.")

    # ── Dados base ────────────────────────────────────────────────────────────
    df_vendas = query("SELECT * FROM public_gold_sales.vendas_temporais")

    # Filtro de mês
    meses = sorted(df_vendas["mes_venda"].unique().tolist())
    meses_labels = {m: ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"][m-1] for m in meses}
    col_f1, col_f2 = st.columns([1, 4])
    with col_f1:
        mes_sel = st.selectbox(
            "Filtrar por mês",
            options=["Todos"] + meses,
            format_func=lambda x: "Todos os meses" if x == "Todos" else meses_labels.get(x, x),
        )

    df = df_vendas if mes_sel == "Todos" else df_vendas[df_vendas["mes_venda"] == mes_sel]

    # ── KPIs ─────────────────────────────────────────────────────────────────
    receita_total = df["receita"].sum()
    total_vendas  = len(df)
    ticket_medio  = df["receita"].mean() if total_vendas > 0 else 0
    clientes_unicos = df["id_cliente"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💵 Receita Total",    fmt_brl(receita_total))
    k2.metric("🧾 Total de Vendas",  f"{total_vendas:,}")
    k3.metric("🎯 Ticket Médio",     fmt_brl(ticket_medio))
    k4.metric("👤 Clientes Únicos",  f"{clientes_unicos:,}")

    st.markdown("---")

    # ── Gráfico 1: Receita diária ─────────────────────────────────────────────
    df_dia = df.groupby("data_venda")["receita"].sum().reset_index().sort_values("data_venda")
    fig1 = px.line(
        df_dia, x="data_venda", y="receita",
        color_discrete_sequence=[COLORS["primary"]],
    )
    fig1.update_traces(line_width=2.5, fill="tozeroy",
                       fillcolor="rgba(124,111,205,0.12)")
    apply_layout(fig1, "📈 Receita Diária", height=320)
    fig1.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
    st.plotly_chart(fig1, use_container_width=True)

    col_g2, col_g3 = st.columns(2)

    # ── Gráfico 2: Receita por dia da semana ──────────────────────────────────
    ordem_dia = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
    df_sem = df.groupby("dia_semana_nome")["receita"].sum().reset_index()
    df_sem["dia_semana_nome"] = pd.Categorical(df_sem["dia_semana_nome"], categories=ordem_dia, ordered=True)
    df_sem = df_sem.sort_values("dia_semana_nome")

    with col_g2:
        fig2 = px.bar(
            df_sem, x="dia_semana_nome", y="receita",
            color_discrete_sequence=[COLORS["secondary"]],
        )
        apply_layout(fig2, "📅 Receita por Dia da Semana")
        fig2.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
        fig2.update_layout(xaxis_title="", yaxis_title="Receita")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Gráfico 3: Volume por hora ────────────────────────────────────────────
    df_hora = df.groupby("hora_venda")["id_venda"].count().reset_index()
    df_hora.columns = ["hora_venda", "vendas"]

    with col_g3:
        fig3 = px.bar(
            df_hora, x="hora_venda", y="vendas",
            color_discrete_sequence=[COLORS["accent"]],
        )
        apply_layout(fig3, "🕐 Volume de Vendas por Hora")
        fig3.update_layout(xaxis_title="Hora", yaxis_title="Nº de Vendas")
        st.plotly_chart(fig3, use_container_width=True)

    # ── Gráfico 4: Receita por canal ──────────────────────────────────────────
    col_g4, col_g5 = st.columns(2)
    df_canal = df.groupby("canal_venda")["receita"].sum().reset_index()
    with col_g4:
        fig4 = px.pie(
            df_canal, names="canal_venda", values="receita",
            color_discrete_sequence=COLORS["chart"],
            hole=0.45,
        )
        apply_layout(fig4, "📡 Receita por Canal")
        st.plotly_chart(fig4, use_container_width=True)

    # ── Gráfico 5: Top categorias ─────────────────────────────────────────────
    df_cat = df.groupby("categoria")["receita"].sum().reset_index().sort_values("receita", ascending=True).tail(8)
    with col_g5:
        fig5 = px.bar(
            df_cat, x="receita", y="categoria", orientation="h",
            color_discrete_sequence=[COLORS["primary"]],
        )
        apply_layout(fig5, "🏷️ Top Categorias por Receita")
        fig5.update_xaxes(tickprefix="R$ ", tickformat=",.0f")
        st.plotly_chart(fig5, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — CLIENTES
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "👥 Clientes":
    st.title("👥 Customer Success — Segmentação de Clientes")
    st.markdown("Análise de perfil, segmentação e valor dos clientes.")

    df_cli = query("SELECT * FROM public_gold_cs.clientes_segmentacao ORDER BY ranking_receita")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_cli    = len(df_cli)
    vip_count    = len(df_cli[df_cli["segmento_cliente"] == "VIP"])
    receita_vip  = df_cli[df_cli["segmento_cliente"] == "VIP"]["receita_total"].sum()
    ticket_geral = df_cli["ticket_medio"].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Total Clientes",  f"{total_cli:,}")
    k2.metric("⭐ Clientes VIP",    f"{vip_count:,}")
    k3.metric("💎 Receita VIP",     fmt_brl(receita_vip))
    k4.metric("🎯 Ticket Médio",    fmt_brl(ticket_geral))

    st.markdown("---")

    col_g1, col_g2 = st.columns(2)

    # ── Gráfico 1: Distribuição por segmento (donut) ─────────────────────────
    df_seg = df_cli.groupby("segmento_cliente").size().reset_index(name="count")
    with col_g1:
        fig1 = px.pie(
            df_seg, names="segmento_cliente", values="count",
            color_discrete_sequence=[COLORS["primary"], COLORS["secondary"], COLORS["accent"]],
            hole=0.5,
        )
        apply_layout(fig1, "🍩 Distribuição por Segmento")
        st.plotly_chart(fig1, use_container_width=True)

    # ── Gráfico 2: Receita por segmento ──────────────────────────────────────
    df_seg_rec = df_cli.groupby("segmento_cliente")["receita_total"].sum().reset_index()
    with col_g2:
        fig2 = px.bar(
            df_seg_rec, x="segmento_cliente", y="receita_total",
            color="segmento_cliente",
            color_discrete_sequence=[COLORS["primary"], COLORS["secondary"], COLORS["accent"]],
        )
        apply_layout(fig2, "💰 Receita por Segmento")
        fig2.update_yaxes(tickprefix="R$ ", tickformat=",.0f")
        fig2.update_layout(showlegend=False, xaxis_title="", yaxis_title="Receita")
        st.plotly_chart(fig2, use_container_width=True)

    col_g3, col_g4 = st.columns(2)

    # ── Gráfico 3: Top 10 clientes ───────────────────────────────────────────
    df_top10 = df_cli.nsmallest(10, "ranking_receita").sort_values("receita_total")
    with col_g3:
        fig3 = px.bar(
            df_top10, x="receita_total", y="nome_cliente", orientation="h",
            color_discrete_sequence=[COLORS["success"]],
        )
        apply_layout(fig3, "🏆 Top 10 Clientes por Receita")
        fig3.update_xaxes(tickprefix="R$ ", tickformat=",.0f")
        fig3.update_layout(yaxis_title="", xaxis_title="Receita Total")
        st.plotly_chart(fig3, use_container_width=True)

    # ── Gráfico 4: Clientes por Estado ────────────────────────────────────────
    df_estado = df_cli.groupby("estado").size().reset_index(name="count").sort_values("count", ascending=False)
    with col_g4:
        fig4 = px.bar(
            df_estado, x="estado", y="count",
            color_discrete_sequence=[COLORS["secondary"]],
        )
        apply_layout(fig4, "🗺️ Clientes por Estado")
        fig4.update_layout(xaxis_title="Estado", yaxis_title="Nº de Clientes")
        st.plotly_chart(fig4, use_container_width=True)

    # ── Tabela detalhada ──────────────────────────────────────────────────────
    st.markdown("### 📋 Tabela Detalhada")
    seg_filter = st.selectbox("Filtrar por segmento", ["Todos", "VIP", "TOP_TIER", "REGULAR"])
    df_show = df_cli if seg_filter == "Todos" else df_cli[df_cli["segmento_cliente"] == seg_filter]

    df_display = df_show[[
        "ranking_receita", "nome_cliente", "estado", "segmento_cliente",
        "receita_total", "total_compras", "ticket_medio", "data_cadastro"
    ]].copy()
    df_display["receita_total"] = df_display["receita_total"].apply(lambda x: fmt_brl(x) if pd.notna(x) else "—")
    df_display["ticket_medio"]  = df_display["ticket_medio"].apply(lambda x: fmt_brl(x) if pd.notna(x) else "—")
    df_display.columns = ["Rank", "Cliente", "Estado", "Segmento", "Receita", "Compras", "Ticket Médio", "Cadastro"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — PRICING
# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "💰 Pricing":
    st.title("💰 Pricing — Competitividade de Preços")
    st.markdown("Posicionamento dos nossos preços vs. concorrência.")

    df_price = query("SELECT * FROM public_gold_pricing.precos_competitividade")

    # Filtro de categoria
    categorias = sorted(df_price["categoria"].unique().tolist())
    cat_sel = st.multiselect("Filtrar por categoria", categorias, default=categorias)
    df_p = df_price[df_price["categoria"].isin(cat_sel)] if cat_sel else df_price

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_prod   = len(df_p)
    mais_caros   = len(df_p[df_p["classificacao_preco"] == "MAIS_CARO_QUE_TODOS"])
    mais_baratos = len(df_p[df_p["classificacao_preco"] == "MAIS_BARATO_QUE_TODOS"])
    dif_media    = df_p["diferenca_percentual_vs_media"].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📦 Produtos Monitorados", f"{total_prod:,}")
    k2.metric("🔴 Mais Caros que Todos", f"{mais_caros:,}")
    k3.metric("🟢 Mais Baratos que Todos", f"{mais_baratos:,}")
    k4.metric("📊 Diferença Média vs Mercado", f"{dif_media:+.1f}%")

    st.markdown("---")

    col_g1, col_g2 = st.columns(2)

    # ── Gráfico 1: Distribuição por classificação ─────────────────────────────
    df_class = df_p.groupby("classificacao_preco").size().reset_index(name="count")
    color_map = {
        "MAIS_CARO_QUE_TODOS":   "#eb5757",
        "ACIMA_DA_MEDIA":        "#f2994a",
        "NA_MEDIA":              "#56ccf2",
        "ABAIXO_DA_MEDIA":       "#6fcf97",
        "MAIS_BARATO_QUE_TODOS": "#27ae60",
    }
    with col_g1:
        fig1 = px.pie(
            df_class, names="classificacao_preco", values="count",
            color="classificacao_preco", color_discrete_map=color_map,
            hole=0.45,
        )
        apply_layout(fig1, "🎯 Posicionamento vs Concorrência")
        st.plotly_chart(fig1, use_container_width=True)

    # ── Gráfico 2: Diferença % por categoria ─────────────────────────────────
    df_cat_dif = df_p.groupby("categoria")["diferenca_percentual_vs_media"].mean().reset_index()
    df_cat_dif = df_cat_dif.sort_values("diferenca_percentual_vs_media")
    df_cat_dif["cor"] = df_cat_dif["diferenca_percentual_vs_media"].apply(
        lambda x: "#6fcf97" if x < 0 else "#eb5757"
    )
    with col_g2:
        fig2 = px.bar(
            df_cat_dif, x="categoria", y="diferenca_percentual_vs_media",
            color="cor", color_discrete_map="identity",
        )
        apply_layout(fig2, "📊 Competitividade por Categoria (%)")
        fig2.update_layout(showlegend=False, xaxis_title="", yaxis_title="Diferença %")
        fig2.update_yaxes(ticksuffix="%")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Gráfico 3: Scatter preço vs volume ────────────────────────────────────
    fig3 = px.scatter(
        df_p,
        x="diferenca_percentual_vs_media",
        y="quantidade_total",
        color="classificacao_preco",
        size="receita_total",
        hover_name="nome_produto",
        hover_data=["nosso_preco", "preco_medio_concorrentes"],
        color_discrete_map=color_map,
        size_max=40,
    )
    apply_layout(fig3, "⚖️ Competitividade × Volume de Vendas", height=400)
    fig3.update_layout(
        xaxis_title="Diferença % vs Média Concorrentes",
        yaxis_title="Quantidade Vendida",
    )
    fig3.update_xaxes(ticksuffix="%")
    fig3.add_vline(x=0, line_dash="dash", line_color="rgba(255,255,255,0.3)")
    st.plotly_chart(fig3, use_container_width=True)

    # ── Tabela de alertas ─────────────────────────────────────────────────────
    st.markdown("### 🚨 Produtos em Alerta (mais caros que todos os concorrentes)")
    df_alert = df_p[df_p["classificacao_preco"] == "MAIS_CARO_QUE_TODOS"][[
        "nome_produto", "categoria", "nosso_preco",
        "preco_maximo_concorrentes", "diferenca_percentual_vs_media", "receita_total"
    ]].sort_values("diferenca_percentual_vs_media", ascending=False)

    if len(df_alert) > 0:
        df_alert_show = df_alert.copy()
        df_alert_show["nosso_preco"]               = df_alert_show["nosso_preco"].apply(fmt_brl)
        df_alert_show["preco_maximo_concorrentes"] = df_alert_show["preco_maximo_concorrentes"].apply(fmt_brl)
        df_alert_show["diferenca_percentual_vs_media"] = df_alert_show["diferenca_percentual_vs_media"].apply(lambda x: f"+{x:.1f}%")
        df_alert_show["receita_total"]             = df_alert_show["receita_total"].apply(fmt_brl)
        df_alert_show.columns = ["Produto", "Categoria", "Nosso Preço", "Máx. Concorrente", "Dif. %", "Receita"]
        st.dataframe(df_alert_show, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nenhum produto está mais caro que todos os concorrentes.")
